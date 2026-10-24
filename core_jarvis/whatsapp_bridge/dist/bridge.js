"use strict";
/**
 * Global-Wave / Stark-Core WhatsApp Baileys Bridge (v2.0 Multimodal)
 * Supports Text, Images, PDF/ZIP/Documents, Voice Notes (PTT), Videos & Stickers.
 * Automatically downloads incoming media to output/whatsapp_media/ for HUD display.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const baileys_1 = __importStar(require("@whiskeysockets/baileys"));
const readline = __importStar(require("readline"));
const qrcodeTerminal = __importStar(require("qrcode-terminal"));
const qrcode_1 = __importDefault(require("qrcode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const crypto = __importStar(require("crypto"));
const pino_1 = __importDefault(require("pino"));
const silentLogger = (0, pino_1.default)({ level: "silent" });
function emit(event) {
    process.stdout.write(JSON.stringify(event) + "\n");
}
function parseArgs() {
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
function unwrapMessage(message) {
    if (!message)
        return null;
    if (message.ephemeralMessage?.message)
        return unwrapMessage(message.ephemeralMessage.message);
    if (message.viewOnceMessage?.message)
        return unwrapMessage(message.viewOnceMessage.message);
    if (message.viewOnceMessageV2?.message)
        return unwrapMessage(message.viewOnceMessageV2.message);
    if (message.documentWithCaptionMessage?.message)
        return unwrapMessage(message.documentWithCaptionMessage.message);
    if (message.editedMessage?.message)
        return unwrapMessage(message.editedMessage.message);
    if (message.protocolMessage?.editedMessage)
        return unwrapMessage(message.protocolMessage.editedMessage);
    return message;
}
function extractMessageText(rawMessage) {
    const message = unwrapMessage(rawMessage);
    if (!message)
        return "";
    if (typeof message.conversation === "string" && message.conversation)
        return message.conversation;
    if (message.extendedTextMessage?.text)
        return message.extendedTextMessage.text;
    if (message.imageMessage?.caption)
        return message.imageMessage.caption;
    if (message.videoMessage?.caption)
        return message.videoMessage.caption;
    if (message.documentMessage?.caption)
        return message.documentMessage.caption;
    return "";
}
const MIME_EXTENSION_MAP = {
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
function sanitizeFileName(rawName, fallbackExt) {
    const base = path.basename(rawName || `file${fallbackExt}`);
    // Keep only safe ASCII characters to prevent Path Traversal and URL encoding issues
    const safe = base.replace(/[^a-zA-Z0-9._-]/g, "_");
    return safe.length > 3 ? safe : `attachment_${Date.now()}${fallbackExt}`;
}
async function extractAndDownloadMedia(msg, mediaDir) {
    const unwrapped = unwrapMessage(msg.message);
    if (!unwrapped)
        return null;
    let mediaType = null;
    let mediaObj = null;
    if (unwrapped.imageMessage) {
        mediaType = "image";
        mediaObj = unwrapped.imageMessage;
    }
    else if (unwrapped.documentMessage) {
        mediaType = "document";
        mediaObj = unwrapped.documentMessage;
    }
    else if (unwrapped.audioMessage) {
        mediaType = "audio";
        mediaObj = unwrapped.audioMessage;
    }
    else if (unwrapped.videoMessage) {
        mediaType = "video";
        mediaObj = unwrapped.videoMessage;
    }
    else if (unwrapped.stickerMessage) {
        mediaType = "sticker";
        mediaObj = unwrapped.stickerMessage;
    }
    if (!mediaType || !mediaObj)
        return null;
    try {
        if (!fs.existsSync(mediaDir)) {
            fs.mkdirSync(mediaDir, { recursive: true });
        }
        const mimeType = mediaObj.mimetype || "application/octet-stream";
        const defaultExt = MIME_EXTENSION_MAP[mimeType.split(";")[0].trim()] || ".bin";
        const originalName = mediaObj.fileName || `${mediaType}_${Date.now()}${defaultExt}`;
        const safeName = sanitizeFileName(originalName, defaultExt);
        const uniquePrefix = `${Date.now()}_${crypto.randomBytes(3).toString("hex")}`;
        const savedFileName = `wa_${uniquePrefix}_${safeName}`;
        const fullDiskPath = path.join(mediaDir, savedFileName);
        const buffer = await (0, baileys_1.downloadMediaMessage)(msg, "buffer", {}, {
            logger: silentLogger,
            reuploadRequest: async (m) => m,
        });
        fs.writeFileSync(fullDiskPath, buffer);
        const fileSize = buffer.length;
        return {
            media_type: mediaType,
            mime_type: mimeType,
            file_name: originalName,
            file_size: fileSize,
            url: `/output/whatsapp_media/${savedFileName}`,
            local_path: fullDiskPath,
        };
    }
    catch (err) {
        console.error(`[WhatsApp Media Download Error] ${err?.message ?? String(err)}`);
        return null;
    }
}
async function main() {
    const { authDir, mediaDir } = parseArgs();
    if (!fs.existsSync(authDir)) {
        fs.mkdirSync(authDir, { recursive: true });
    }
    if (!fs.existsSync(mediaDir)) {
        fs.mkdirSync(mediaDir, { recursive: true });
    }
    const { state, saveCreds } = await (0, baileys_1.useMultiFileAuthState)(authDir);
    const { version } = await (0, baileys_1.fetchLatestWaWebVersion)().catch(() => ({
        version: [2, 3000, 1051456098],
    }));
    let sock = null;
    function startSocket() {
        sock = (0, baileys_1.default)({
            version,
            auth: state,
            logger: silentLogger,
            printQRInTerminal: false,
            browser: baileys_1.Browsers.windows("Desktop"),
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
                    const qrDataUrl = await qrcode_1.default.toDataURL(qr, { margin: 2, scale: 8 });
                    const htmlContent = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>JARVIS WhatsApp QR</title></head><body style="background:#0b0f19;color:#58a6ff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:sans-serif;"><div style="background:#161b26;padding:32px;border-radius:16px;text-align:center;"><h2>JARVIS WhatsApp Bağlantısı</h2><img src="${qrDataUrl}" width="320" height="320" /></div></body></html>`;
                    fs.writeFileSync(path.join(authDir, "qr.html"), htmlContent, "utf-8");
                }
                catch (err) {
                    console.error("[QR Render Warning]", err);
                }
                emit({ type: "qr", data: qr });
            }
            if (connection === "close") {
                const statusCode = lastDisconnect?.error?.output?.statusCode ?? 500;
                if (statusCode === baileys_1.DisconnectReason.loggedOut) {
                    emit({ type: "status", status: "disconnected" });
                    emit({ type: "error", message: "Logged out from WhatsApp" });
                }
                else {
                    emit({ type: "status", status: "disconnected" });
                    setTimeout(startSocket, 2500);
                }
            }
            else if (connection === "open") {
                emit({ type: "status", status: "connected" });
            }
        });
        sock.ev.on("messages.upsert", async ({ messages }) => {
            for (const msg of messages) {
                if (!msg.message || msg.key.fromMe)
                    continue;
                const chatJid = msg.key.remoteJid || "";
                if (!chatJid || chatJid === "status@broadcast")
                    continue;
                const senderJid = msg.key.participant || chatJid;
                const pushName = msg.pushName || "";
                let text = extractMessageText(msg.message).trim();
                // Check and download any attached media (Image, PDF, ZIP, Audio, Video)
                const mediaInfo = await extractAndDownloadMedia(msg, mediaDir);
                // If message has neither text nor media, skip
                if (!text && !mediaInfo)
                    continue;
                // Provide descriptive fallback text if user sent a file without caption
                if (!text && mediaInfo) {
                    const typeLabels = {
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
    rl.on("line", async (line) => {
        const trimmed = line.trim();
        if (!trimmed)
            return;
        let cmd;
        try {
            cmd = JSON.parse(trimmed);
        }
        catch {
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
            }
            catch (err) {
                emit({
                    type: "error",
                    message: err?.message ?? String(err),
                    request_id: cmd.request_id,
                    jid: cmd.jid,
                });
            }
        }
        else if (cmd.type === "delete" && sock) {
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
            }
            catch (err) {
                emit({
                    type: "error",
                    message: err?.message ?? String(err),
                    request_id: cmd.request_id,
                    jid: cmd.jid,
                });
            }
        }
        else if (cmd.type === "disconnect" && sock) {
            await sock.logout().catch(() => { });
            process.exit(0);
        }
    });
}
main().catch((err) => {
    emit({ type: "error", message: String(err) });
    process.exit(1);
});
