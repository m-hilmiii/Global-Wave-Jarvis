"""
Global Wave v3.1 - Standalone YouTube OAuth 2.0 Authorization Helper
Run this script directly to authorize your YouTube channel once:
    python auth_youtube.py
"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from engine.uploader_youtube import run_oauth_flow, get_channel_profile

def main():
    print("=" * 60)
    print("   [+] GLOBAL WAVE v3.1 - YOUTUBE OAUTH 2.0 KURULUMU (FAZ 2)")
    print("=" * 60)
    print("[1/3] client_secret.json doğrulanıyor...")
    
    secret_path = BASE_DIR / "config" / "client_secret.json"
    if not secret_path.exists():
        print(f"[HATA] {secret_path} bulunamadı!")
        sys.exit(1)
        
    print(f"[2/3] Tarayıcı açılıyor ve Google onay penceresi başlatılıyor...")
    print(">>> Lütfen açılan pencerede YouTube kanalınızın bağlı olduğu Google hesabını seçin.")
    print(">>> 'Gelişmiş' -> '... uygulamasına git' diyerek izin verin.")
    print("-" * 60)
    
    try:
        creds = run_oauth_flow()
        print("-" * 60)
        print("[3/3] Token başarıyla kaydedildi: config/youtube_tokens.json")
        
        profile = get_channel_profile()
        if profile and profile.get("is_connected"):
            print("=" * 60)
            print(f"🎉 TEBRİKLER! KANAL BAŞARIYLA BAĞLANDI:")
            print(f"   Kanal Adı: {profile.get('title')}")
            print(f"   Kanal ID:  {profile.get('channel_id')}")
            print(f"   Abone:     {profile.get('subscriber_count')}")
            print(f"   Video:     {profile.get('video_count')}")
            print("=" * 60)
            print("Artık Web HUD arayüzünden tek tıkla YouTube Shorts yükleyebilirsiniz!")
        else:
            print("[UYARI] Token kaydedildi fakat kanal bilgileri çekilemedi.")
    except Exception as e:
        print(f"\n[HATA] Yetkilendirme sırasında hata oluştu: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()