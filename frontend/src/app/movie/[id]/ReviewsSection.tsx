"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Star, Pencil, Trash2 } from "lucide-react";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  createMovieReview,
  deleteMovieReview,
  fetchMovieReviews,
  ReviewItem,
  updateMovieReview,
  voteMovieReview,
} from "@/lib/api";

function StarInput({ value, onChange }: { value: number; onChange: (rating: number) => void }) {
  const [hovered, setHovered] = useState(0);
  return (
    <div role="radiogroup" aria-label="Movie rating" style={{ display: "flex", gap: 6 }}>
      {[1, 2, 3, 4, 5].map((rating) => (
        <button
          key={rating}
          type="button"
          role="radio"
          aria-checked={value === rating}
          aria-label={`${rating} star${rating > 1 ? "s" : ""}`}
          onMouseEnter={() => setHovered(rating)}
          onMouseLeave={() => setHovered(0)}
          onFocus={() => setHovered(rating)}
          onClick={() => onChange(rating)}
          style={{ border: 0, background: "transparent", padding: 2, cursor: "pointer" }}
        >
          <Star size={28} fill={(hovered || value) >= rating ? "#facc15" : "none"} color="#facc15" />
        </button>
      ))}
    </div>
  );
}

export default function ReviewsSection({ movieId }: { movieId: string }) {
  const { getToken } = useAuth();
  const { isSignedIn } = useUser();
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [average, setAverage] = useState(0);
  const [count, setCount] = useState(0);
  const [rating, setRating] = useState(0);
  const [text, setText] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const ownReview = useMemo(() => items.find((item) => item.is_owner), [items]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchMovieReviews(movieId);
      setItems(result.items);
      setAverage(result.average_rating);
      setCount(result.rating_count);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load reviews");
    } finally {
      setLoading(false);
    }
  }, [movieId]);

  useEffect(() => { void load(); }, [load]);

  const handleVoteAction = async (reviewId: string, targetVote: number) => {
    const targetReview = items.find(r => r.id === reviewId);
    if (!targetReview) return;

    const previousVote = targetReview.user_vote || 0;
    const previousHelpfulCount = targetReview.helpful_count || 0;
    let nextVote = 0;

    if (previousVote === targetVote) {
      nextVote = 0;
    } else {
      nextVote = targetVote;
    }

    const optimisticHelpfulCount = previousHelpfulCount + (targetVote === 1 ? (previousVote === 1 ? -1 : 1) : (previousVote === 1 ? -1 : 0));

    setItems(prev => prev.map(r =>
      r.id === reviewId
        ? { ...r, user_vote: nextVote, helpful_count: Math.max(0, optimisticHelpfulCount) }
        : r
    ));

    try {
      const token = await getToken();
      if (!token) throw new Error("Sign in to vote on reviews");

      const res = await voteMovieReview(reviewId, token, targetVote);
      setItems(prev => prev.map(r =>
        r.id === reviewId ? { ...r, user_vote: res.user_vote } : r
      ));
    } catch (err) {
      console.error("[VOTE ROLLBACK] Reverting optimistic UI adjustment:", err);
      setItems(prev => prev.map(r =>
        r.id === reviewId ? { ...r, user_vote: previousVote, helpful_count: previousHelpfulCount } : r
      ));
    }
  };

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!rating) { setError("Choose a rating from 1 to 5 stars"); return; }
    const token = await getToken();
    if (!token) { setError("Sign in to review this movie"); return; }
    setSaving(true);
    try {
      if (editingId) await updateMovieReview(editingId, token, { rating, text });
      else await createMovieReview(movieId, token, { rating, text });
      setRating(0); setText(""); setEditingId(null); await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save review");
    } finally { setSaving(false); }
  }

  function startEdit(review: ReviewItem) {
    setEditingId(review.id); setRating(review.rating); setText(review.text);
  }

  async function remove(reviewId: string) {
    const token = await getToken();
    if (!token || !window.confirm("Delete your review?")) return;
    await deleteMovieReview(reviewId, token); await load();
  }

  return (
    <section aria-labelledby="reviews-heading" style={{ padding: "40px 5% 80px" }}>
      <div className="glass-panel" style={{ padding: 28 }}>
        <h2 id="reviews-heading" style={{ fontSize: 28, marginBottom: 8 }}>Ratings & Reviews</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>
          <strong>{average.toFixed(1)} / 5</strong> from {count} review{count === 1 ? "" : "s"}
        </p>

        {isSignedIn ? (
          <form onSubmit={submit} style={{ display: "grid", gap: 14, marginBottom: 30 }}>
            <StarInput value={rating} onChange={setRating} />
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              maxLength={5000}
              rows={4}
              placeholder="Write your review"
              aria-label="Review text"
              style={{ width: "100%", padding: 14, borderRadius: 10, background: "var(--bg-elevated)", color: "var(--text-primary)" }}
            />
            <button className="btn btn-primary" type="submit" disabled={saving || Boolean(ownReview && !editingId)}>
              {saving ? "Saving…" : editingId ? "Update review" : ownReview ? "You already reviewed this movie" : "Post review"}
            </button>
          </form>
        ) : <p style={{ marginBottom: 24 }}>Sign in to rate and review this movie.</p>}

        {error && <p role="alert" style={{ color: "#ef4444" }}>{error}</p>}
        {loading ? <p>Loading reviews…</p> : items.length === 0 ? <p>No reviews yet. Be the first.</p> : (
          <div style={{ display: "grid", gap: 16 }}>
            {items.map((review) => (
              <article key={review.id} className="glass-panel" style={{ padding: 18 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                  <div style={{ flex: 1 }}>
                    <div aria-label={`${review.rating} out of 5 stars`} style={{ color: "#facc15" }}>{"★".repeat(review.rating)}{"☆".repeat(5-review.rating)}</div>
                    <p style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{review.text || "No written review."}</p>
                    
                    {/* Helpfulness Voting Action Array Grid */}
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 12, fontSize: "13px" }}>
                      <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Was this review helpful?</span>
                      
                      {/* Upvote Button */}
                      <button
                        type="button"
                        onClick={() => handleVoteAction(review.id, 1)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 10px",
                          borderRadius: 6,
                          border: "1px solid",
                          fontSize: "12px",
                          cursor: "pointer",
                          background: review.user_vote === 1 ? "rgba(16,185,129,0.15)" : "var(--bg-elevated)",
                          borderColor: review.user_vote === 1 ? "#10b981" : "rgba(255,255,255,0.1)",
                          color: review.user_vote === 1 ? "#34d399" : "var(--text-secondary)"
                        }}
                      >
                        <span>👍</span>
                        <span style={{ fontFamily: "monospace" }}>{review.helpful_count || 0}</span>
                      </button>

                      {/* Downvote Button */}
                      <button
                        type="button"
                        onClick={() => handleVoteAction(review.id, -1)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 10px",
                          borderRadius: 6,
                          border: "1px solid",
                          fontSize: "12px",
                          cursor: "pointer",
                          background: review.user_vote === -1 ? "rgba(244,63,94,0.15)" : "var(--bg-elevated)",
                          borderColor: review.user_vote === -1 ? "#f43f5e" : "rgba(255,255,255,0.1)",
                          color: review.user_vote === -1 ? "#fb7185" : "var(--text-secondary)"
                        }}
                      >
                        <span>👎</span>
                      </button>
                    </div>
                  </div>

                  {review.is_owner && <div style={{ display: "flex", gap: 8 }}>
                    <button type="button" aria-label="Edit review" onClick={() => startEdit(review)} className="btn btn-glass"><Pencil size={16}/></button>
                    <button type="button" aria-label="Delete review" onClick={() => void remove(review.id)} className="btn btn-glass"><Trash2 size={16}/></button>
                  </div>}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

