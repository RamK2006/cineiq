import re

with open('src/app/profile/ProfileClient.tsx', 'r') as f:
    content = f.read()

# Add ShareCardModal import
if 'ShareCardModal' not in content:
    content = content.replace(
        "import { fetchProfileStats, ProfileStats } from '@/lib/api';",
        "import { fetchProfileStats, ProfileStats } from '@/lib/api';\nimport ShareCardModal from '@/components/ShareCardModal';\nimport { Share } from 'lucide-react';"
    )

# Add Modal State
if 'isShareModalOpen' not in content:
    content = content.replace(
        "const [statsError, setStatsError] = useState<string | null>(null);",
        "const [statsError, setStatsError] = useState<string | null>(null);\n  const [isShareModalOpen, setIsShareModalOpen] = useState(false);"
    )

# Add Modal render before the closing main tag
if '<ShareCardModal' not in content:
    modal_jsx = """
      <ShareCardModal 
        isOpen={isShareModalOpen} 
        onClose={() => setIsShareModalOpen(false)} 
        userName={userName} 
        userAvatar={user?.imageUrl || ''} 
        moviesWatched={stats.movies_watched} 
        radarData={stats.radarData || []} 
        primaryGenre={genrePreferences[0]?.genre || 'Movies'}
      />
    """
    content = content.replace(
        "    </main>",
        modal_jsx + "\n    </main>"
    )

# Add Share button to the Taste Profile header
if '<button onClick={() => setIsShareModalOpen(true)}' not in content:
    share_button = """
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h2 style={{ fontSize: '20px', margin: 0 }}>Taste Profile</h2>
                {hasTasteProfile && !statsLoading && (
                    <button 
                        onClick={() => setIsShareModalOpen(true)}
                        className="btn-primary"
                        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', borderRadius: '20px', fontSize: '14px' }}
                    >
                        <Share size={16} />
                        Share Taste
                    </button>
                )}
            </div>
    """
    
    content = re.sub(
        r"<h2 style=\{\{ fontSize: '20px', marginBottom: '24px' \}\}>Taste Profile</h2>",
        share_button,
        content
    )

with open('src/app/profile/ProfileClient.tsx', 'w') as f:
    f.write(content)
