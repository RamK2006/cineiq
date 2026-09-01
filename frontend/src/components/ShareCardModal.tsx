import React, { useRef, useState, useCallback, useEffect } from 'react';
import { toPng } from 'html-to-image';
import { X, Download, Share2, Loader2 } from 'lucide-react';

interface RadarItem {
  subject: string;
  A: number;
  fullMark: number;
}

interface TopMovie {
  id: string;
  title: string;
  poster_path?: string;
}

interface ShareCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  userName: string;
  userAvatar: string;
  moviesWatched: number;
  radarData: RadarItem[];
  primaryGenre: string;
  topMovies?: TopMovie[]; // Added top movies
}

export default function ShareCardModal({
  isOpen,
  onClose,
  userName,
  userAvatar,
  moviesWatched,
  radarData,
  primaryGenre,
  topMovies = [],
}: ShareCardModalProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isNativeShareSupported, setIsNativeShareSupported] = useState(false);
  const [safeAvatar, setSafeAvatar] = useState<string>('');

  useEffect(() => {
    if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
      setIsNativeShareSupported(true);
    }

    
    const fetchSafeAvatar = async () => {
        if (!userAvatar) return;
        try {
            const response = await fetch(userAvatar, { mode: 'cors' });
            const blob = await response.blob();
            const reader = new FileReader();
            reader.onloadend = () => setSafeAvatar(reader.result as string);
            reader.readAsDataURL(blob);
        } catch (e) {
            console.warn('Failed to load base64 avatar for card', e);
            setSafeAvatar(userAvatar); 
        }
    };
    
    fetchSafeAvatar();
  }, [userAvatar]);

  const generateImageBlob = useCallback(async (): Promise<Blob | null> => {
    if (!cardRef.current) return null;
    setIsGenerating(true);
    try {
      const dataUrl = await toPng(cardRef.current, {
        quality: 1.0,
        pixelRatio: 2, 
        cacheBust: true,
        style: {
            transform: 'scale(1)',
            transformOrigin: 'top left',
        }
      });
      const res = await fetch(dataUrl);
      return await res.blob();
    } catch (err) {
      console.error('Failed to generate image', err);
      return null;
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const handleDownload = async () => {
    const blob = await generateImageBlob();
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CineIQ_Taste_Card_${userName.replace(/\s+/g, '_')}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleNativeShare = async () => {
    const blob = await generateImageBlob();
    if (!blob) return;
    
    const file = new File([blob], 'cineiq_taste_profile.png', { type: 'image/png' });
    if (navigator.share && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({
          title: `${userName}'s CineIQ Taste Profile`,
          text: `Check out my movie taste profile on CineIQ! I lean heavily towards ${primaryGenre}.`,
          files: [file],
        });
      } catch (err) {
        console.warn('Share rejected or failed', err);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative bg-[#1A1C23] rounded-2xl border border-white/10 p-6 w-full max-w-md shadow-2xl flex flex-col my-auto">
        <button onClick={onClose} className="absolute top-4 right-4 text-white/50 hover:text-white"><X size={24} /></button>
        <h2 className="text-xl font-bold mb-6 text-center text-white">Share Your Taste</h2>

        <div className="relative w-full aspect-[9/16] bg-black rounded-xl overflow-hidden shadow-inner flex items-center justify-center">
            <div 
                ref={cardRef}
                className="absolute"
                style={{
                    width: '1080px',
                    height: '1920px',
                    transform: 'scale(0.25)', 
                    transformOrigin: 'center center',
                    background: 'linear-gradient(145deg, #12141A 0%, #1A1C23 100%)',
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '100px 80px',
                    fontFamily: 'Inter, sans-serif'
                }}
            >
                <div style={{ position: 'absolute', top: '-10%', right: '-20%', width: '1000px', height: '1000px', background: 'radial-gradient(circle, rgba(139,92,246,0.15) 0%, rgba(0,0,0,0) 70%)', borderRadius: '50%' }} />
                <div style={{ position: 'absolute', bottom: '-10%', left: '-20%', width: '1200px', height: '1200px', background: 'radial-gradient(circle, rgba(236,72,153,0.1) 0%, rgba(0,0,0,0) 70%)', borderRadius: '50%' }} />

                <div style={{ display: 'flex', alignItems: 'center', gap: '40px', zIndex: 10 }}>
                    {safeAvatar ? (
                        <img src={safeAvatar} alt="Avatar" style={{ width: '200px', height: '200px', borderRadius: '50%', objectFit: 'cover', border: '8px solid rgba(255,255,255,0.1)' }} crossOrigin="anonymous" />
                    ) : (
                        <div style={{ width: '200px', height: '200px', borderRadius: '50%', background: 'linear-gradient(135deg, #8B5CF6, #EC4899)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '80px', color: 'white', fontWeight: 'bold' }}>{userName[0]}</div>
                    )}
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '40px', textTransform: 'uppercase', letterSpacing: '4px' }}>CineIQ Member</span>
                        <h1 style={{ color: 'white', fontSize: '80px', fontWeight: 900, margin: 0, lineHeight: 1.1 }}>{userName}</h1>
                    </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', background: 'rgba(255,255,255,0.03)', padding: '60px', borderRadius: '40px', marginTop: '100px', border: '2px solid rgba(255,255,255,0.05)', zIndex: 10, backdropFilter: 'blur(20px)' }}>
                    <div>
                        <div style={{ color: 'white', fontSize: '100px', fontWeight: 900, lineHeight: 1 }}>{moviesWatched}</div>
                        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '30px', textTransform: 'uppercase', letterSpacing: '2px', marginTop: '10px' }}>Movies Watched</div>
                    </div>
                    <div>
                        <div style={{ color: '#EC4899', fontSize: '100px', fontWeight: 900, lineHeight: 1 }}>#{radarData[0]?.subject || 'N/A'}</div>
                        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '30px', textTransform: 'uppercase', letterSpacing: '2px', marginTop: '10px' }}>Top Genre</div>
                    </div>
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', marginTop: '80px', zIndex: 10 }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '30px', justifyContent: 'center' }}>
                        {radarData.slice(0, 4).map((d, i) => (
                            <div key={i} style={{ background: 'rgba(255,255,255,0.05)', padding: '30px 40px', borderRadius: '100px', border: '2px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: '20px' }}>
                                <span style={{ color: 'white', fontSize: '40px', fontWeight: 700 }}>{d.subject}</span>
                                <span style={{ color: '#8B5CF6', fontSize: '40px', fontWeight: 900 }}>{d.A}%</span>
                            </div>
                        ))}
                    </div>
                </div>

                {topMovies && topMovies.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '40px', zIndex: 10 }}>
                        <h3 style={{ color: 'rgba(255,255,255,0.5)', fontSize: '30px', textTransform: 'uppercase', letterSpacing: '4px', marginBottom: '40px' }}>Top Favorites</h3>
                        <div style={{ display: 'flex', gap: '40px' }}>
                            {topMovies.map((m, i) => (
                                <div key={i} style={{ width: '220px', height: '330px', borderRadius: '24px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.5)', background: '#222' }}>
                                    {m.poster_path ? (
                                        <img src={`https://image.tmdb.org/t/p/w500${m.poster_path}`} alt={m.title} style={{ width: '100%', height: '100%', objectFit: 'cover' }} crossOrigin="anonymous" />
                                    ) : (
                                        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', padding: '20px', textAlign: 'center', fontSize: '24px', fontWeight: 'bold' }}>{m.title}</div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 'auto', paddingTop: '80px', borderTop: '2px solid rgba(255,255,255,0.1)', zIndex: 10 }}>
                    <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '36px', fontWeight: 600, letterSpacing: '6px' }}>CINEIQ.COM</div>
                </div>
            </div>
        </div>

        <div className="flex flex-col gap-3 mt-6">
          {isNativeShareSupported && (
            <button onClick={handleNativeShare} disabled={isGenerating} className="w-full bg-pink-500 hover:bg-pink-600 text-white rounded-xl py-4 font-bold text-lg flex items-center justify-center gap-2">
              {isGenerating ? <Loader2 className="animate-spin" /> : <Share2 />} Share to Story
            </button>
          )}
          <button onClick={handleDownload} disabled={isGenerating} className={`w-full rounded-xl py-4 font-bold text-lg flex items-center justify-center gap-2 ${isNativeShareSupported ? 'bg-white/10 text-white' : 'bg-purple-600 text-white'}`}>
            {isGenerating ? <Loader2 className="animate-spin" /> : <Download />} Download Image
          </button>
        </div>
      </div>
    </div>
  );
}
