"use strict";
/**
 * Global-Wawe WhatsApp Baileys Bridge
 * Real-time connection with QR Code in terminal, Web JSON events,
 * and robust inbox persistence for all message types (including ephemeral/quotes).
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
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const pino_1 = __importDefault(require("pino"));
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
    return { authDir: path.resolve(process.cwd(), authDir) };
}
function extractMessageText(message) {
    if (!message)
        return "";
    if (typeof message.conversation === "string" && message.conversation) {
        return message.conversation;
    }
    if (message.extendedTextMessage?.text) {
        return message.extendedTextMessage.text;
    }
    if (message.ephemeralMessage?.message) {
        return extractMessageText(message.ephemeralMessage.message);
    }
    if (message.viewOnceMessage?.message) {
        return extractMessageText(message.viewOnceMessage.message);
    }
    if (message.viewOnceMessageV2?.message) {
        return extractMessageText(message.viewOnceMessageV2.message);
    }
    if (message.documentWithCaptionMessage?.message) {
        return extractMessageText(message.documentWithCaptionMessage.message);
    }
    if (message.imageMessage?.caption) {
        return message.imageMessage.caption;
    }
    if (message.videoMessage?.caption) {
        return message.videoMessage.caption;
    }
    if (message.editedMessage?.message) {
        return extractMessageText(message.editedMessage.message);
    }
    if (message.protocolMessage?.editedMessage) {
        return extractMessageText(message.protocolMessage.editedMessage);
    }
    return "";
}
function resolveSenderInfo(authDir, jid, pushName) {
    const rawNum = jid.replace(/\D/g, "");
    try {
        const contactsPath = path.resolve(authDir, "..", "contacts.json");
        if (fs.existsSync(contactsPath)) {
            const raw = fs.readFileSync(contactsPath, "utf-8").replace(/^\uFEFF/, "");
            const data = JSON.parse(raw);
            const contacts = data.contacts || [];
            for (const c of contacts) {
                const cNum = (c.phone || "").replace(/\D/g, "");
                if (cNum && rawNum && (cNum.endsWith(rawNum) || rawNum.endsWith(cNum))) {
                    return { name: c.name, phone: c.phone || rawNum };
                }
                if (c.lid && (jid.includes(c.lid) || rawNum.includes(c.lid))) {
                    const displayName = c.full_name ? `${c.name} (${c.full_name})` : c.name;
                    return { name: displayName, phone: c.phone || rawNum };
                }
                if (pushName && ((c.full_name && pushName.toLowerCase().includes(c.full_name.toLowerCase())) ||
                    (c.name && pushName.toLowerCase().includes(c.name.toLowerCase())) ||
                    (c.relationship && c.relationship.toLowerCase() === "baba" && pushName.toLowerCase().includes("yaşar")))) {
                    const displayName = c.full_name ? `${c.name} (${c.full_name})` : `${c.name} (${pushName})`;
                    return { name: displayName, phone: c.phone || rawNum };
                }
            }
        }
    }
    catch (e) { }
    return { name: pushName || rawNum || "Bilinmeyen Numara", phone: rawNum };
}
function markChatAsReadInInbox(authDir, chatId) {
    try {
        const inboxPath = path.resolve(authDir, "..", "whatsapp_inbox.json");
        if (!fs.existsSync(inboxPath))
            return;
        const raw = fs.readFileSync(inboxPath, "utf-8").replace(/^\uFEFF/, "");
        const inbox = JSON.parse(raw);
        let changed = false;
        const cleanChatId = chatId.replace(/\D/g, "");
        for (const msg of inbox) {
            const msgChat = (msg.chat_jid || "").replace(/\D/g, "");
            const msgSender = (msg.sender_jid || "").replace(/\D/g, "");
            const msgPhone = (msg.phone || "").replace(/\D/g, "");
            if (msg.chat_jid === chatId ||
                msg.sender_jid === chatId ||
                (cleanChatId && (msgChat.includes(cleanChatId) || msgSender.includes(cleanChatId) || msgPhone.includes(cleanChatId)))) {
                if (msg.unread) {
                    msg.unread = false;
                    changed = true;
                }
            }
        }
        if (changed) {
            fs.writeFileSync(inboxPath, JSON.stringify(inbox, null, 2), "utf-8");
            emit({ type: "chat_read", chatId });
        }
    }
    catch (err) { }
}
function saveMessageToInbox(authDir, entry) {
    try {
        const inboxPath = path.resolve(authDir, "..", "whatsapp_inbox.json");
        let inbox = [];
        if (fs.existsSync(inboxPath)) {
            try {
                const raw = fs.readFileSync(inboxPath, "utf-8").replace(/^\uFEFF/, "");
                inbox = JSON.parse(raw);
            }
            catch { }
        }
        if (!inbox.some((m) => m.id === entry.id)) {
            inbox.push(entry);
            if (inbox.length > 100)
                inbox = inbox.slice(-100);
            fs.writeFileSync(inboxPath, JSON.stringify(inbox, null, 2), "utf-8");
        }
    }
    catch (err) {
        console.error("[Bridge Inbox Error]", err);
    }
}
async function main() {
    const { authDir } = parseArgs();
    if (!fs.existsSync(authDir)) {
        fs.mkdirSync(authDir, { recursive: true });
    }
    const { state, saveCreds } = await (0, baileys_1.useMultiFileAuthState)(authDir);
    const { version } = await (0, baileys_1.fetchLatestWaWebVersion)().catch(() => ({
        version: [2, 3000, 1051456098],
    }));
    const silentLogger = (0, pino_1.default)({ level: "silent" });
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
        sock.ev.on("connection.update", (update) => {
            const { connection, lastDisconnect, qr } = update;
            if (qr) {
                console.log("\n==================================================");
                console.log("   JARVIS WHATSAPP QR KODU (TELEFONUNUZDAN OKUTUN)");
                console.log("==================================================\n");
                qrcodeTerminal.generate(qr, { small: true });
                console.log("\n==================================================");
                console.log("Telefonunuzdan: WhatsApp -> Ayarlar -> Bagli Cihazlar -> Cihaz Bagla");
                console.log("Tarayicida gormek icin: " + path.join(authDir, "qr.html"));
                console.log("==================================================\n");
                try {
                    const qrUrl = "https://api.qrserver.com/v1/create-qr-code/?size=350x350&data=" + encodeURIComponent(qr);
                    const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>JARVIS WhatsApp QR Baglanti</title>
  <style>
    body { background: #0b0f19; color: #58a6ff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { background: #161b26; border: 1px solid #30363d; border-radius: 16px; padding: 32px; text-align: center; box-shadow: 0 12px 32px rgba(0,0,0,0.6); max-width: 440px; }
    h2 { color: #00d2ff; margin-top: 0; }
    .qr-box { background: white; padding: 16px; border-radius: 12px; display: inline-block; margin: 20px 0; }
    img { display: block; border-radius: 4px; }
    p { color: #c9d1d9; font-size: 15px; line-height: 1.5; }
    .sub { color: #8b949e; font-size: 13px; }
  </style>
</head>
<body>
  <div class="card">
    <h2>JARVIS WhatsApp Baglantisi</h2>
    <p>Telefonunuzdan <b>WhatsApp &gt; Bagli Cihazlar &gt; Cihaz Bagla</b> secenegini acin ve kameranizi asagidaki koda tutun:</p>
    <div class="qr-box">
      <img src="${qrUrl}" alt="QR Code" width="350" height="350" />
    </div>
    <p class="sub">Baglanti saglandiktan sonra bu sayfayi kapatabilirsiniz.</p>
  </div>
</body>
</html>`;
                    fs.writeFileSync(path.join(authDir, "qr.html"), htmlContent, "utf-8");
                }
                catch (e) { }
                emit({ type: "qr", data: qr });
            }
            if (connection === "close") {
                const statusCode = lastDisconnect?.error?.output?.statusCode ?? 500;
                if (statusCode === baileys_1.DisconnectReason.loggedOut) {
                    console.log("[WhatsApp] Oturum sonlandirildi (Logged out).");
                    emit({ type: "status", status: "disconnected" });
                    emit({ type: "error", message: "Logged out from WhatsApp" });
                }
                else {
                    console.log("[WhatsApp] Baglanti koptu veya yenileniyor...");
                    emit({ type: "status", status: "disconnected" });
                    setTimeout(startSocket, 2500);
                }
            }
            else if (connection === "open") {
                console.log("\n==================================================");
                console.log("[OK] TEBRIKLER! WHATSAPP OTURUMU BASARIYLA BAGLANDI!");
                console.log("JARVIS artik telefonunuz uzerinden mesaj atabilir.");
                console.log("Bu pencereyi kapatabilirsiniz.");
                console.log("==================================================\n");
                emit({ type: "status", status: "connected" });
            }
        });
        sock.ev.on("chats.update", (chats) => {
            for (const chat of chats) {
                if (chat.unreadCount === 0 && chat.id) {
                    markChatAsReadInInbox(authDir, chat.id);
                }
            }
        });
        sock.ev.on("messages.upsert", ({ messages }) => {
            for (const msg of messages) {
                if (!msg.message || msg.key.fromMe)
                    continue;
                const text = extractMessageText(msg.message).trim();
                const chatJid = msg.key.remoteJid || "";
                const senderJid = msg.key.participant || chatJid;
                const pushName = msg.pushName || "";
                const primaryJid = chatJid.includes("@s.whatsapp.net") ? chatJid : senderJid;
                if (chatJid && text) {
                    const { name, phone } = resolveSenderInfo(authDir, primaryJid, pushName);
                    const now = new Date();
                    const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
                    const inboxEntry = {
                        id: msg.key.id,
                        sender_jid: senderJid,
                        chat_jid: chatJid,
                        sender_name: name,
                        phone: phone,
                        text: text,
                        time: timeStr,
                        timestamp: Date.now() / 1000,
                        unread: true,
                    };
                    saveMessageToInbox(authDir, inboxEntry);
                    emit({
                        type: "message",
                        jid: chatJid,
                        sender: senderJid,
                        text,
                        message_id: msg.key.id,
                        pushName,
                        sender_name: name,
                        phone,
                    });
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
                await sock.sendMessage(cmd.jid, { text: cmd.text });
                console.log(`[WhatsApp] Mesaj iletildi -> ${cmd.jid}`);
                emit({ type: "sent", jid: cmd.jid });
            }
            catch (err) {
                console.error(`[WhatsApp Hata] Gonderilemedi: ${err?.message ?? String(err)}`);
                emit({ type: "error", message: err?.message ?? String(err) });
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
                console.log(`[WhatsApp] Mesaj herkesten silindi -> ${cmd.message_id}`);
                emit({ type: "deleted", jid: cmd.jid, message_id: cmd.message_id });
            }
            catch (err) {
                console.error(`[WhatsApp Hata] Silinemedi: ${err?.message ?? String(err)}`);
                emit({ type: "error", message: err?.message ?? String(err) });
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
