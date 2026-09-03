/**
 * frontend/src/app/rooms/page.tsx
 * -------------------------------
 * Public Room Directory discovery page with filters, live counters, and Create Room modal (#209).
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface Room {
  id: string;
  title: string;
  movie_id: string | null;
  is_public: boolean;
  max_participants: number;
  current_participants: number;
  tags: string[];
}

export default function RoomsDirectoryPage() {
  const router = useRouter();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [search, setSearch] = useState('');
  const [genre, setGenre] = useState('');
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // New room form state
  const [newTitle, setNewTitle] = useState('');
  const [newMovieId, setNewMovieId] = useState('');
  const [newMaxParticipants, setNewMaxParticipants] = useState(10);
  const [newTags, setNewTags] = useState('');

  const fetchRooms = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (genre) params.append('genre', genre);

      const res = await fetch(`/api/v1/rooms/public?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setRooms(data);
      }
    } catch (err) {
      console.error('Failed to fetch public rooms', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRooms();
    const interval = setInterval(fetchRooms, 10000); // Poll for live updates
    return () => clearInterval(interval);
  }, [search, genre]);

  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/rooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle,
          movie_id: newMovieId || null,
          max_participants: Number(newMaxParticipants),
          is_public: true,
          tags: newTags.split(',').map((t) => t.trim()).filter(Boolean),
        }),
      });

      if (res.ok) {
        const room = await res.json();
        setIsModalOpen(false);
        router.push(`/room/${room.id}`);
      }
    } catch (err) {
      console.error('Failed to create room', err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Public Watch Rooms (#209)</h1>
          <p className="text-slate-400">Discover active watch parties and join live screening sessions.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 rounded-lg font-medium transition"
        >
          Create Room
        </button>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <input
          type="text"
          placeholder="Search by room title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500"
        />
        <input
          type="text"
          placeholder="Filter by genre tag (e.g., Sci-Fi, Action)..."
          value={genre}
          onChange={(e) => setGenre(e.target.value)}
          className="bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500"
        />
      </div>

      {/* Room Grid */}
      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading active rooms...</div>
      ) : rooms.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/50 rounded-xl border border-slate-800">
          <p className="text-slate-400 text-lg">No public rooms found matching your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rooms.map((room) => (
            <div key={room.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-xl font-semibold">{room.title}</h3>
                  <span className="bg-indigo-950 text-indigo-400 text-xs px-2.5 py-1 rounded-full border border-indigo-800/50">
                    {room.current_participants} / {room.max_participants} joined
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 mb-6">
                  {room.tags.map((tag, idx) => (
                    <span key={idx} className="bg-slate-800 text-slate-300 text-xs px-2 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
              <button
                disabled={room.current_participants >= room.max_participants}
                onClick={() => router.push(`/room/${room.id}`)}
                className={`w-full py-2.5 rounded-lg font-medium transition ${
                  room.current_participants >= room.max_participants
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                }`}
              >
                {room.current_participants >= room.max_participants ? 'Room Full' : 'Join Room'}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create Room Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6">
            <h2 className="text-2xl font-bold mb-4">Create Watch Party Room</h2>
            <form onSubmit={handleCreateRoom} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Room Title</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g., Sci-Fi Movie Night"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Movie ID (optional)</label>
                <input
                  type="text"
                  value={newMovieId}
                  onChange={(e) => setNewMovieId(e.target.value)}
                  placeholder="TMDB Movie ID"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Max Participants</label>
                <input
                  type="number"
                  min={2}
                  max={50}
                  value={newMaxParticipants}
                  onChange={(e) => setNewMaxParticipants(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={newTags}
                  onChange={(e) => setNewTags(e.target.value)}
                  placeholder="Sci-Fi, Action, Premiere"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg font-medium transition"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
