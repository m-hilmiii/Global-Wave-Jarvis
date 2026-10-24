"""
Global-Wawe / Stark-Core - Wake-on-LAN (WOL) Management Tool
Enables remote hardware wake-up (S5 power state -> Powered On) via UDP Broadcast Magic Packet.
Discovers local network interfaces (Realtek PCIe GbE etc.) and provides remote webhook instructions.
"""

import binascii
import logging
import platform
import re
import socket
import subprocess
from typing import Dict, Any, List, Optional

logger = logging.getLogger("Jarvis.WOL")

DEFAULT_WOL_PORT = 9

class WOLTool:
    def __init__(self):
        pass

    @staticmethod
    def clean_mac(mac_address: str) -> str:
        """Strips delimiters and validates a 12-character hexadecimal MAC address."""
        clean = re.sub(r"[^0-9a-fA-F]", "", str(mac_address).strip())
        if len(clean) != 12:
            raise ValueError(f"Geçersiz MAC adresi: '{mac_address}'. MAC adresi 12 onaltılık (hex) karakter olmalıdır.")
        return clean.upper()

    @staticmethod
    def format_mac(clean_mac: str, delimiter: str = ":") -> str:
        """Formats 12-char hex string into standard MAC format (e.g. 9C:6B:00:B2:A2:0F)."""
        clean = re.sub(r"[^0-9a-fA-F]", "", clean_mac).upper()
        return delimiter.join(clean[i:i+2] for i in range(0, 12, 2))

    def create_magic_packet(self, mac_address: str) -> bytes:
        """
        Creates a standard 102-byte Wake-on-LAN Magic Packet:
        6 bytes of 0xFF followed by 16 repetitions of the 6-byte target MAC address.
        """
        clean = self.clean_mac(mac_address)
        mac_bytes = binascii.unhexlify(clean)
        magic_packet = b"\xff" * 6 + mac_bytes * 16
        return magic_packet

    def send_magic_packet(
        self,
        mac_address: str,
        broadcast_ip: str = "255.255.255.255",
        port: int = DEFAULT_WOL_PORT
    ) -> Dict[str, Any]:
        """
        Broadcasts the magic packet over UDP to wake the target computer.
        """
        try:
            packet = self.create_magic_packet(mac_address)
            formatted_mac = self.format_mac(mac_address)

            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                # Attempt sending
                sock.sendto(packet, (broadcast_ip, port))

            logger.info(f"[WOL] Magic packet broadcasted to {formatted_mac} via {broadcast_ip}:{port}")
            return {
                "success": True,
                "target_mac": formatted_mac,
                "broadcast_ip": broadcast_ip,
                "port": port,
                "packet_size_bytes": len(packet),
                "message": f"Sihirli Paket (Magic Packet) başarıyla gönderildi: {formatted_mac} ({broadcast_ip}:{port})"
            }
        except Exception as e:
            logger.error(f"[WOL] Magic packet dispatch error: {e}")
            return {
                "success": False,
                "target_mac": mac_address,
                "error": str(e),
                "message": f"Sihirli paket gönderilemedi: {str(e)}"
            }

    def discover_local_adapters(self) -> List[Dict[str, str]]:
        """
        Scans Windows/Linux network adapters to identify physical NICs (Ethernet) capable of WOL.
        """
        adapters = []
        os_type = platform.system().lower()

        if "windows" in os_type:
            try:
                cmd = "getmac /v /fo list"
                output = subprocess.check_output(cmd, shell=True, text=True, errors="replace")
                current = {}
                for line in output.splitlines():
                    line = line.strip()
                    if not line:
                        if current.get("mac") and current.get("mac") != "N/A":
                            adapters.append(current)
                        current = {}
                        continue

                    if line.startswith("Connection Name:"):
                        current["connection_name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Network Adapter:"):
                        current["adapter_name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Physical Address:"):
                        raw_mac = line.split(":", 1)[1].strip()
                        if raw_mac and raw_mac != "N/A":
                            current["mac"] = raw_mac.replace("-", ":").upper()
                    elif line.startswith("Transport Name:"):
                        current["transport"] = line.split(":", 1)[1].strip()

                if current.get("mac") and current.get("mac") != "N/A":
                    adapters.append(current)
            except Exception as e:
                logger.warning(f"[WOL] getmac discovery warning: {e}")

        # Fallback or supplemental hostname / local IP lookup
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = "Unknown"
            local_ip = "127.0.0.1"

        return adapters

    def get_host_wol_identity(self) -> Dict[str, Any]:
        """
        Returns this host's primary physical Ethernet MAC address, local IP, and setup instructions.
        """
        adapters = self.discover_local_adapters()
        primary_ethernet = None

        # Prioritize physical PCIe / GbE Ethernet controllers
        for a in adapters:
            name_lower = (a.get("connection_name", "") + " " + a.get("adapter_name", "")).lower()
            if "ethernet" in name_lower or "pcie" in name_lower or "realtek" in name_lower or "intel" in name_lower:
                if "vpn" not in name_lower and "warp" not in name_lower and "virtual" not in name_lower:
                    primary_ethernet = a
                    break

        if not primary_ethernet and adapters:
            primary_ethernet = adapters[0]

        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = "DESKTOP"
            local_ip = "127.0.0.1"

        primary_mac = primary_ethernet.get("mac", "") if primary_ethernet else ""

        return {
            "hostname": hostname,
            "local_ip": local_ip,
            "primary_mac": primary_mac,
            "primary_adapter": primary_ethernet.get("adapter_name", "Bilinmeyen Adaptör") if primary_ethernet else "",
            "connection_name": primary_ethernet.get("connection_name", "") if primary_ethernet else "",
            "all_adapters": adapters,
            "bios_wol_instructions": [
                "1. BIOS Ayarı: Bilgisayarı yeniden başlatıp BIOS'a girin (Genelde DEL veya F2 tuşu).",
                "2. 'Power Management Setup' veya 'Advanced' menüsünden 'Wake on LAN' (veya 'PCIe Device Power On') seçeneğini ENABLED yapın.",
                "3. Windows Aygıt Yöneticisi: Ağ Bağdaştırıcıları -> Realtek PCIe GbE Controller -> Özellikler -> Güç Yönetimi sekmesinde 'Bu cihazın bilgisayarı başlatmasına izin ver' ve 'Yalnızca sihirli bir paketin bilgisayarı uyandırmasına izin ver' seçeneklerini işaretleyin.",
                "4. Hızlı Başlatmayı Kapatın: Denetim Masası -> Güç Seçenekleri -> Güç düğmelerinin yapacaklarını seçin -> 'Hızlı başlatmayı aç' seçeneğinin işaretini kaldırın (Tam S5 durumunda LAN yongasına elektrik gitmesi için zorunludur)."
            ],
            "wan_forwarding_guide": {
                "router_port": 9,
                "protocol": "UDP",
                "router_target_ip": local_ip,
                "recommendation": "Dış ağdan (telefon 4G/5G) bilgisayarı açmak için modeminizin arayüzünde Port Yönlendirme (Port Forwarding) bölümünden UDP 9 portunu bilgisayarınızın yerel IP adresine yönlendirin."
            }
        }

wol_tool = WOLTool()
