#!/usr/bin/env python3
"""
FFmpeg + Sixel Yaklaşımı Demo
Uniform medya işleme ve preview generation testi
"""
import sys
import logging
from pathlib import Path

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ffmpeg_availability():
    """FFmpeg kurulumu test et"""
    print("🔍 FFmpeg Kurulum Testi")
    print("=" * 50)
    
    try:
        from utils.ffmpeg_utils import ffmpeg_processor, is_ffmpeg_available
        
        if is_ffmpeg_available():
            print("✅ FFmpeg BULUNDU ve kullanıma hazır!")
            print(f"   - FFmpeg: {ffmpeg_processor.ffmpeg_available}")
            print(f"   - FFprobe: {ffmpeg_processor.ffprobe_available}")
        else:
            print("❌ FFmpeg BULUNAMADI")
            print("   Kurulum için: sudo apt install ffmpeg  # Ubuntu/Debian")
            print("                 sudo pacman -S ffmpeg   # Arch")
            print("                 sudo dnf install ffmpeg # Fedora")
            
        return is_ffmpeg_available()
        
    except ImportError as e:
        print(f"❌ FFmpeg utils import hatası: {e}")
        return False

def test_media_info(media_file: Path):
    """Medya dosyası bilgilerini test et"""
    print(f"\n📊 Medya Bilgisi Testi: {media_file.name}")
    print("=" * 50)
    
    try:
        from utils.ffmpeg_utils import get_media_info
        
        if not media_file.exists():
            print(f"❌ Dosya bulunamadı: {media_file}")
            return False
        
        info = get_media_info(media_file)
        if info:
            print("✅ Medya bilgisi başarıyla alındı:")
            print(f"   📁 Dosya: {info['filename']}")
            print(f"   📊 Boyut: {info['size'] / (1024*1024):.1f} MB")
            print(f"   🎬 Format: {info['format']}")
            print(f"   📐 Çözünürlük: {info.get('width', 0)}x{info.get('height', 0)}")
            print(f"   ⏱️ Süre: {info.get('duration', 0):.1f} saniye")
            print(f"   🎞️ FPS: {info.get('fps', 0):.1f}")
            print(f"   🎵 Ses: {'Var' if info.get('has_audio', False) else 'Yok'}")
            print(f"   🎥 Codec: {info.get('video_codec', 'N/A')}")
            print(f"   🔧 FFmpeg: {'Evet' if info.get('ffmpeg_available', False) else 'Hayır'}")
            return True
        else:
            print("❌ Medya bilgisi alınamadı")
            return False
            
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        return False

def test_thumbnail_generation(media_file: Path, output_dir: Path):
    """Thumbnail oluşturma test et"""
    print(f"\n🖼️ Thumbnail Oluşturma Testi")
    print("=" * 50)
    
    try:
        from utils.ffmpeg_utils import generate_thumbnail
        
        if not media_file.exists():
            print(f"❌ Kaynak dosya bulunamadı: {media_file}")
            return False
        
        # Output dizinini oluştur
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Thumbnail path
        thumbnail_path = output_dir / f"{media_file.stem}_thumbnail.jpg"
        
        # Thumbnail oluştur
        print(f"🔄 Thumbnail oluşturuluyor: {thumbnail_path}")
        success = generate_thumbnail(
            media_file, 
            thumbnail_path, 
            size=(400, 300), 
            timestamp=1.0
        )
        
        if success and thumbnail_path.exists():
            size_kb = thumbnail_path.stat().st_size / 1024
            print(f"✅ Thumbnail başarıyla oluşturuldu!")
            print(f"   📁 Dosya: {thumbnail_path}")
            print(f"   📊 Boyut: {size_kb:.1f} KB")
            return True
        else:
            print("❌ Thumbnail oluşturulamadı")
            return False
            
    except Exception as e:
        print(f"❌ Thumbnail test hatası: {e}")
        return False

def test_optimization(media_file: Path, output_dir: Path):
    """Video optimizasyon test et"""
    print(f"\n⚡ Video Optimizasyon Testi")
    print("=" * 50)
    
    try:
        from utils.ffmpeg_utils import optimize_for_wallpaper
        
        if not media_file.exists():
            print(f"❌ Kaynak dosya bulunamadı: {media_file}")
            return False
        
        # Output dizinini oluştur
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Optimized path
        optimized_path = output_dir / f"{media_file.stem}_optimized.mp4"
        
        # Optimizasyon yap
        print(f"🔄 Video optimize ediliyor: {optimized_path}")
        print("   (Bu işlem biraz zaman alabilir...)")
        
        success = optimize_for_wallpaper(media_file, optimized_path)
        
        if success and optimized_path.exists():
            original_size = media_file.stat().st_size / (1024*1024)
            optimized_size = optimized_path.stat().st_size / (1024*1024)
            compression_ratio = ((original_size - optimized_size) / original_size) * 100
            
            print(f"✅ Video optimizasyonu başarılı!")
            print(f"   📁 Orijinal: {original_size:.1f} MB")
            print(f"   📁 Optimize: {optimized_size:.1f} MB")
            print(f"   📉 Sıkıştırma: %{compression_ratio:.1f}")
            return True
        else:
            print("❌ Video optimizasyonu başarısız")
            return False
            
    except Exception as e:
        print(f"❌ Optimizasyon test hatası: {e}")
        return False

def find_test_media():
    """Test için medya dosyası bul"""
    print("\n🔍 Test Medyası Aranıyor...")
    
    # Olası test dosyası konumları
    test_locations = [
        Path.home() / "Videos",
        Path.home() / "Downloads", 
        Path("/tmp"),
        Path(".")
    ]
    
    # Desteklenen formatlar
    video_extensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv']
    
    for location in test_locations:
        if location.exists():
            for ext in video_extensions:
                test_files = list(location.glob(f"*{ext}"))
                if test_files:
                    test_file = test_files[0]
                    print(f"✅ Test dosyası bulundu: {test_file}")
                    return test_file
    
    print("❌ Test için uygun medya dosyası bulunamadı")
    print("   Lütfen ~/Videos, ~/Downloads veya mevcut dizine bir video dosyası koyun")
    return None

def main():
    """Ana demo fonksiyonu"""
    print("🎬 FFmpeg + Sixel Yaklaşımı Demo")
    print("=" * 60)
    print("Uniform medya işleme ve preview generation sistemi")
    print()
    
    # 1. FFmpeg kurulum testi
    if not test_ffmpeg_availability():
        print("\n❌ FFmpeg bulunamadı - demo sonlandırılıyor")
        print("Lütfen önce FFmpeg kurun ve tekrar deneyin")
        return False
    
    # 2. Test medyası bul
    test_media = find_test_media()
    if not test_media:
        print("\n⚠️ Test medyası bulunamadı - sadece FFmpeg testi yapıldı")
        return True
    
    # Output dizini
    output_dir = Path("./ffmpeg_demo_output")
    
    # 3. Medya bilgisi testi
    test_media_info(test_media)
    
    # 4. Thumbnail testi
    test_thumbnail_generation(test_media, output_dir)
    
    # 5. Optimizasyon testi (sadece büyük dosyalar için)
    file_size_mb = test_media.stat().st_size / (1024*1024)
    if file_size_mb > 10:  # 10MB'dan büyükse optimize et
        test_optimization(test_media, output_dir)
    else:
        print(f"\n⚡ Video Optimizasyon Testi")
        print("=" * 50)
        print(f"📊 Dosya boyutu ({file_size_mb:.1f} MB) küçük - optimizasyon atlandı")
    
    print(f"\n🎉 Demo tamamlandı!")
    if output_dir.exists():
        print(f"📁 Çıktı dosyaları: {output_dir}")
        
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo kullanıcı tarafından iptal edildi")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo hatası: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)