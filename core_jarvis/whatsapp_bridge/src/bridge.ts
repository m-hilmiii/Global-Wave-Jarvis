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
  const { version } = await fetchLatestWaWebVersion().catch(() => ({
    version: [2, 3000, 1051456098] as [number, number, number],
  }));

  let sock: WASocket | null = null;

  function startSocket(): void {
    sock = makeWASocket({
      version,
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
        try {
          const qrDataUrl = await QRCode.toDataURL(qr, { margin: 2, scale: 8 });
          const htmlContent = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>JARVIS WhatsApp QR</title></head><body style="background:#0b0f19;color:#58a6ff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:sans-serif;"><div style="background:#161b26;padding:32px;border-radius:16px;text-align:center;"><h2>JARVIS WhatsApp Bağlantısı</h2><img src="${qrDataUrl}" width="320" height="320" /></div></body></html>`;
          fs.writeFileSync(path.join(authDir, "qr.html"), htmlContent, "utf-8");
        } catch (err) {
          console.error("[QR Render Warning]", err);
        }
        emit({ type: "qr", data: qr });
      }

      if (connection === "close") {
        const statusCode = (lastDisconnect?.error as any)?.output?.statusCode ?? 500;
        if (statusCode === DisconnectReason.loggedOut) {
          emit({ type: "status", status: "disconnected" });
          emit({ type: "error", message: "Logged out from WhatsApp" });
        } else {
          emit({ type: "status", status: "disconnected" });
          setTimeout(startSocket, 2500);
        }
      } else if (connection === "open") {
        emit({ type: "status", status: "connected" });
      }
    });

    sock.ev.on("messages.upsert", async ({ messages }) => {
      for (const msg of messages) {
        if (!msg.message || msg.key.fromMe) continue;

        const chatJid = msg.key.remoteJid || "";
        if (!chatJid || chatJid === "status@broadcast") continue;

        const senderJid = msg.key.participant || chatJid;
        const pushName = msg.pushName || "";
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

        // Single-writer architecture: emit full event to Python WhatsAppDaemon
        emit({
          type: "message",
          jid: chatJid,
          sender: senderJid,
          text,
          message_id: msg.key.id,
          pushName,
          media: mediaInfo,
        });
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
