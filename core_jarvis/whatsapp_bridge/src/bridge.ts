/**
 * Global-Wave / Stark-Core WhatsApp Baileys Bridge (v2.0 Multimodal)
 * Supports Text, Images, PDF/ZIP/Documents, Voice Notes (PTT), Videos & Stickers.
 * Automatically downloads incoming media to output/whatsapp_media/ for HUD display.
 */

import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  WASocket,
  fetchLatestWaWebVersion,
  Browsers,
  downloadMediaMessage,
  WAMessage,
} from "@whiskeysockets/baileys";
import * as readline from "readline";
import * as qrcodeTerminal from "qrcode-terminal";
import QRCode from "qrcode";
import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import pino from "pino";

const silentLogger = pino({ level: "silent" });

function emit(event: Record<string, unknown>): void {
  process.stdout.write(JSON.stringify(event) + "\n");
}

function parseArgs(): { authDir: string; mediaDir: string } {
  const args = process.argv.slice(2);
  let authDir = "./auth";
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--auth-dir" && i + 1 < args.length) {
      authDir = args[i + 1];
      break;
    }
  }
  const resolvedAuth = path.resolve(process.cwd(), authDir);
  // Save media under Global-Wawe/output/whatsapp_media so FastAPI /output static mount serves it directly
  const workspaceRoot = path.resolve(resolvedAuth, "..", "..");
  const mediaDir = path.join(workspaceRoot, "output", "whatsapp_media");
  return { authDir: resolvedAuth, mediaDir };
}

/** Unwraps ephemeral, viewOnce, or documentWithCaption containers to get the core message object */
function unwrapMessage(message: any): any {
  if (!message) return null;
  if (message.ephemeralMessage?.message) return unwrapMessage(message.ephemeralMessage.message);
  if (message.viewOnceMessage?.message) return unwrapMessage(message.viewOnceMessage.message);
  if (message.viewOnceMessageV2?.message) return unwrapMessage(message.viewOnceMessageV2.message);
  if (message.documentWithCaptionMessage?.message) return unwrapMessage(message.documentWithCaptionMessage.message);
  if (message.editedMessage?.message) return unwrapMessage(message.editedMessage.message);
  if (message.protocolMessage?.editedMessage) return unwrapMessage(message.protocolMessage.editedMessage);
  return message;
}

function extractMessageText(rawMessage: any): string {
  const message = unwrapMessage(rawMessage);
  if (!message) return "";
  if (typeof message.conversation === "string" && message.conversation) return message.conversation;
  if (message.extendedTextMessage?.text) return message.extendedTextMessage.text;
  if (message.imageMessage?.caption) return message.imageMessage.caption;
  if (message.videoMessage?.caption) return message.videoMessage.caption;
  if (message.documentMessage?.caption) return message.documentMessage.caption;
  return "";
}

interface MediaAttachment {
  media_type: "image" | "document" | "audio" | "video" | "sticker";
  mime_type: string;
  file_name: string;
  file_size: number;
  url: string;
  local_path: string;
}

const MIME_EXTENSION_MAP: Record<string, string> = {
  "image/jpeg": ".jpg",
  "image/png": ".png",
  "image/webp": ".webp",
  "image/gif": ".gif",
  "application/pdf": ".pdf",
  "application/zip": ".zip",
  "application/x-zip-compressed": ".zip",
  "application/x-rar-compressed": ".rar",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
  "text/plain": ".txt",
  "audio/ogg; codecs=opus": ".ogg",
  "audio/ogg": ".ogg",
  "audio/mpeg": ".mp3",
  "audio/mp4": ".m4a",
  "video/mp4": ".mp4",
};

function sanitizeFileName(rawName: string, fallbackExt: string): string {
  const base = path.basename(rawName || `file${fallbackExt}`);
  // Keep only safe ASCII characters to prevent Path Traversal and URL encoding issues
  const safe = base.replace(/[^a-zA-Z0-9._-]/g, "_");
  return safe.length > 3 ? safe : `attachment_${Date.now()}${fallbackExt}`;
}

async function extractAndDownloadMedia(
  msg: WAMessage,
  mediaDir: string
): Promise<MediaAttachment | null> {
  const unwrapped = unwrapMessage(msg.message);
  if (!unwrapped) return null;

  let mediaType: MediaAttachment["media_type"] | null = null;
  let mediaObj: any = null;

  if (unwrapped.imageMessage) {
    mediaType = "image";
    mediaObj = unwrapped.imageMessage;
  } else if (unwrapped.documentMessage) {
    mediaType = "document";
    mediaObj = unwrapped.documentMessage;
  } else if (unwrapped.audioMessage) {
    mediaType = "audio";
    mediaObj = unwrapped.audioMessage;
  } else if (unwrapped.videoMessage) {
    mediaType = "video";
    mediaObj = unwrapped.videoMessage;
  } else if (unwrapped.stickerMessage) {
    mediaType = "sticker";
    mediaObj = unwrapped.stickerMessage;
  }

  if (!mediaType || !mediaObj) return null;

  try {
    if (!fs.existsSync(mediaDir)) {
      fs.mkdirSync(mediaDir, { recursive: true });
    }

    const mimeType: string = mediaObj.mimetype || "application/octet-stream";
    const defaultExt = MIME_EXTENSION_MAP[mimeType.split(";")[0].trim()] || ".bin";
    const originalName: string =
      mediaObj.fileName || `${mediaType}_${Date.now()}${defaultExt}`;
    const safeName = sanitizeFileName(originalName, defaultExt);
    const uniquePrefix = `${Date.now()}_${crypto.randomBytes(3).toString("hex")}`;
    const savedFileName = `wa_${uniquePrefix}_${safeName}`;
    const fullDiskPath = path.join(mediaDir, savedFileName);

    const buffer = await downloadMediaMessage(
      msg,
      "buffer",
      {},
      {
        logger: silentLogger,
        reuploadRequest: async (m) => m,
      }
    );

    fs.writeFileSync(fullDiskPath, buffer as Buffer);
    const fileSize = (buffer as Buffer).length;

    return {
      media_type: mediaType,
      mime_type: mimeType,
      file_name: originalName,
      file_size: fileSize,
      url: `/output/whatsapp_media/${savedFileName}`,
      local_path: fullDiskPath,
    };
  } catch (err: any) {
    console.error(`[WhatsApp Media Download Error] ${err?.message ?? String(err)}`);
    return null;
  }
}

async function main(): Promise<void> {
  const { authDir, mediaDir } = parseArgs();
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }
  if (!fs.existsSync(mediaDir)) {
    fs.mkdirSync(mediaDir, { recursive: true });
  }

  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await Promise.race([
    fetchLatestWaWebVersion(),
    new Promise<{ version: [number, number, number] }>((resolve) =>
      setTimeout(() => resolve({ version: [2, 3000, 1051456098] }), 3500)
    ),
  ]).catch(() => ({
    version: [2, 3000, 1051456098] as [number, number, number],
  }));

  const qrStatusPath = path.join(mediaDir, "qr_status.json");
  function writeBridgeStatus(statusObj: Record<string, any>) {
    try {
      if (!fs.existsSync(mediaDir)) fs.mkdirSync(mediaDir, { recursive: true });
      fs.writeFileSync(qrStatusPath, JSON.stringify(statusObj, null, 2), "utf-8");
    } catch (e) {}
  }

  writeBridgeStatus({
    status: "connecting",
    is_connected: false,
    has_qr: false,
    qr_image: null,
    updated_at: Date.now(),
  });

  const storePath = path.resolve(authDir, "..", "..", "data", "baileys_store.json");
  const storeData: { messages: Record<string, any[]> } = { messages: {} };
  const store = {
    readFromFile(fp: string) {
      try {
        if (fs.existsSync(fp)) {
          const parsed = JSON.parse(fs.readFileSync(fp, "utf-8"));
          if (parsed && typeof parsed.messages === "object") {
            storeData.messages = parsed.messages;
          }
        }
      } catch (e) {
        console.error("[Store Read Warning]", e);
      }
    },
    writeToFile(fp: string) {
      try {
        const dir = path.dirname(fp);
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(fp, JSON.stringify(storeData, null, 2), "utf-8");
      } catch (e) {}
    },
    upsertMessage(jid: string, msgObj: any) {
      if (!jid || jid === "status@broadcast") return;
      if (!storeData.messages[jid]) storeData.messages[jid] = [];
      const arr = storeData.messages[jid];
      const mId = msgObj?.key?.id;
      if (mId && arr.some((x) => x?.key?.id === mId)) return;
      arr.push(msgObj);
      if (arr.length > 250) {
        storeData.messages[jid] = arr.slice(-250);
      }
    },
    loadMessages(jid: string, limit: number = 50) {
      const arr = storeData.messages[jid] || [];
      return arr.slice(-limit);
    },
  };
  store.readFromFile(storePath);
  setInterval(() => {
    store.writeToFile(storePath);
  }, 15000);

  let sock: WASocket | null = null;
  let activeVersion: [number, number, number] = version;

  function startSocket(): void {
    sock = makeWASocket({
      version: activeVersion,
      auth: state,
      logger: silentLogger,
      printQRInTerminal: false,
      browser: Browsers.windows("Desktop"),
      syncFullHistory: false,
      connectTimeoutMs: 60000,
      defaultQueryTimeoutMs: 60000,
      keepAliveIntervalMs: 15000,
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        qrcodeTerminal.generate(qr, { small: true });
        let qrDataUrl = "";
        try {
          qrDataUrl = await QRCode.toDataURL(qr, { margin: 2, scale: 8 });
          const htmlContent = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>JARVIS WhatsApp QR</title></head><body style="background:#0b0f19;color:#58a6ff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:sans-serif;"><div style="background:#161b26;padding:32px;border-radius:16px;text-align:center;"><h2>JARVIS WhatsApp Bağlantısı</h2><img src="${qrDataUrl}" width="320" height="320" /></div></body></html>`;
          fs.writeFileSync(path.join(authDir, "qr.html"), htmlContent, "utf-8");
        } catch (err) {
          console.error("[QR Render Warning]", err);
        }
        writeBridgeStatus({
          status: "qr_ready",
          is_connected: false,
          has_qr: true,
          qr_data: qr,
          qr_image: qrDataUrl,
          updated_at: Date.now(),
        });
        emit({ type: "qr", data: qr, qr_image: qrDataUrl });
      }

      if (connection === "close") {
        const statusCode = (lastDisconnect?.error as any)?.output?.statusCode ?? 500;
        const errMsg = (lastDisconnect?.error as any)?.message || String(lastDisconnect?.error || "");
        if (statusCode === 405) {
          activeVersion = [2, 3000, 1051456098];
        }
        if (statusCode === DisconnectReason.loggedOut) {
          writeBridgeStatus({
            status: "disconnected",
            is_connected: false,
            has_qr: false,
            qr_image: null,
            error: "Logged out from WhatsApp",
            updated_at: Date.now(),
          });
          emit({ type: "status", status: "disconnected" });
          emit({ type: "error", message: "Logged out from WhatsApp" });
        } else {
          emit({ type: "status", status: "disconnected", reason: errMsg, code: statusCode });
          setTimeout(startSocket, 2500);
        }
      } else if (connection === "open") {
        writeBridgeStatus({
          status: "connected",
          is_connected: true,
          has_qr: false,
          qr_image: null,
          updated_at: Date.now(),
        });
        emit({ type: "status", status: "connected" });
      }
    });

    sock.ev.on("messages.upsert", async ({ messages }) => {
      for (const msg of messages) {
        if (!msg.message) continue;

        const isFromMe = Boolean(msg.key.fromMe);
        const chatJid = msg.key.remoteJid || "";
        if (!chatJid || chatJid === "status@broadcast") continue;

        store.upsertMessage(chatJid, msg);

        const senderJid = msg.key.participant || (isFromMe ? "me" : chatJid);
        const pushName = isFromMe ? "Mücahit Hilmi (Ben)" : (msg.pushName || "");
        let text = extractMessageText(msg.message).trim();

        // Check and download any attached media (Image, PDF, ZIP, Audio, Video)
        const mediaInfo = await extractAndDownloadMedia(msg, mediaDir);

        // If message has neither text nor media, skip
        if (!text && !mediaInfo) continue;

        // Provide descriptive fallback text if user sent a file without caption
        if (!text && mediaInfo) {
          const typeLabels: Record<string, string> = {
            image: "📷 [Fotoğraf]",
            document: `📄 [Belge: ${mediaInfo.file_name}]`,
            audio: "🎤 [Sesli Mesaj]",
            video: "🎬 [Video]",
            sticker: "🏷️ [Çıkartma]",
          };
          text = typeLabels[mediaInfo.media_type] || `[Dosya: ${mediaInfo.file_name}]`;
        }

        const msgTimestamp = typeof msg.messageTimestamp === "number"
          ? msg.messageTimestamp
          : Number(msg.messageTimestamp) || Math.floor(Date.now() / 1000);

        // Single-writer architecture: emit full event to Python WhatsAppDaemon
        emit({
          type: "message",
          jid: chatJid,
          sender: senderJid,
          text,
          message_id: msg.key.id,
          pushName,
          media: mediaInfo,
          from_me: isFromMe,
          timestamp: msgTimestamp,
        });
      }
    });

    sock.ev.on("messaging-history.set", async ({ messages }) => {
      if (Array.isArray(messages)) {
        const batch: any[] = [];
        for (const msg of messages) {
          if (!msg.message) continue;
          const isFromMe = Boolean(msg.key.fromMe);
          const chatJid = msg.key.remoteJid || "";
          if (!chatJid || chatJid === "status@broadcast") continue;

          store.upsertMessage(chatJid, msg);

          const senderJid = msg.key.participant || (isFromMe ? "me" : chatJid);
          const pushName = isFromMe ? "Mücahit Hilmi (Ben)" : (msg.pushName || "");
          const text = extractMessageText(msg.message).trim();
          if (!text) continue;

          const msgTimestamp = typeof msg.messageTimestamp === "number"
            ? msg.messageTimestamp
            : Number(msg.messageTimestamp) || Math.floor(Date.now() / 1000);

          batch.push({
            jid: chatJid,
            sender: senderJid,
            text,
            message_id: msg.key.id,
            pushName,
            from_me: isFromMe,
            timestamp: msgTimestamp,
            is_history: true,
          });
        }
        store.writeToFile(storePath);
        if (batch.length > 0) {
          emit({ type: "history_batch", messages: batch });
        }
      }
    });
  }

  startSocket();

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  });

  rl.on("line", async (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) return;

    let cmd: any;
    try {
      cmd = JSON.parse(trimmed);
    } catch {
      return;
    }

    if (cmd.type === "send" && sock) {
      try {
        const sentMsg = await sock.sendMessage(cmd.jid, { text: cmd.text });
        emit({
          type: "sent",
          jid: cmd.jid,
          request_id: cmd.request_id,
          message_id: sentMsg?.key?.id,
        });
      } catch (err: any) {
        emit({
          type: "error",
          message: err?.message ?? String(err),
          request_id: cmd.request_id,
          jid: cmd.jid,
        });
      }
    } else if (cmd.type === "send_voice" && sock) {
      try {
        const audioBuffer = fs.readFileSync(cmd.file_path);
        const sentMsg = await sock.sendMessage(cmd.jid, {
          audio: audioBuffer,
          mimetype: "audio/ogg; codecs=opus",
          ptt: true,
        });
        emit({
          type: "sent",
          jid: cmd.jid,
          request_id: cmd.request_id,
          message_id: sentMsg?.key?.id,
        });
      } catch (err: any) {
        emit({
          type: "error",
          message: err?.message ?? String(err),
          request_id: cmd.request_id,
          jid: cmd.jid,
        });
      }
    } else if (cmd.type === "get_chat_messages" && sock) {
      try {
        const limit = cmd.limit || 50;
        const msgs = store.loadMessages(cmd.jid, limit);
        const cleanMsgs = (msgs || []).map((m: any) => ({
          id: m.key.id,
          chat_jid: m.key.remoteJid,
          sender_jid: m.key.participant || (m.key.fromMe ? "me" : m.key.remoteJid),
          sender_name: m.key.fromMe ? "Mücahit Hilmi (Ben)" : (m.pushName || ""),
          text: extractMessageText(m.message).trim(),
          time: new Date((Number(m.messageTimestamp) || Date.now() / 1000) * 1000).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
          timestamp: Number(m.messageTimestamp) || Date.now() / 1000,
          from_me: Boolean(m.key.fromMe),
        })).filter((x: any) => x.text);

        emit({
          type: "chat_messages_loaded",
          jid: cmd.jid,
          request_id: cmd.request_id,
          messages: cleanMsgs,
        });
      } catch (err: any) {
        emit({
          type: "error",
          message: err?.message ?? String(err),
          request_id: cmd.request_id,
        });
      }
    } else if (cmd.type === "delete" && sock) {
      try {
        const key = {
          remoteJid: cmd.jid,
          fromMe: cmd.fromMe !== false,
          id: cmd.message_id,
        };
        await sock.sendMessage(cmd.jid, { delete: key });
        emit({
          type: "deleted",
          jid: cmd.jid,
          message_id: cmd.message_id,
          request_id: cmd.request_id,
        });
      } catch (err: any) {
        emit({
          type: "error",
          message: err?.message ?? String(err),
          request_id: cmd.request_id,
          jid: cmd.jid,
        });
      }
    } else if (cmd.type === "presence" && sock) {
      try {
        await sock.sendPresenceUpdate(cmd.status || "composing", cmd.jid);
      } catch (err: any) {
        // Non-fatal presence update error
      }
    } else if (cmd.type === "disconnect" && sock) {
      await sock.logout().catch(() => {});
      process.exit(0);
    }
  });
}

main().catch((err) => {
  emit({ type: "error", message: String(err) });
  process.exit(1);
});
