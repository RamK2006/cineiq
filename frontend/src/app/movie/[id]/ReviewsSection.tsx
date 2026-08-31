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
  const [distribution, setDistribution] = useState<Record<number, number>>({});
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [rating, setRating] = useState(0);
  const [text, setText] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const ownReview = useMemo(() => items.find((item) => item.is_owner), [items]);

  const load = useCallback(async (pageNum = 1, append = false) => {
    setLoading(true);
    try {
      const result = await fetchMovieReviews(movieId, pageNum, 10);
      setItems((prev) => append ? [...prev, ...result.items] : result.items);
      setAverage(result.average_rating);
      setCount(result.rating_count);
      setDistribution(result.rating_distribution || {});
      setHasMore(pageNum < result.pages);
      setPage(pageNum);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load reviews");
    } finally {
      setLoading(false);
    }
  }, [movieId]);

  useEffect(() => { void load(1, false); }, [load]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!rating) { setError("Choose a rating from 1 to 5 stars"); return; }
    const token = await getToken();
    if (!token) { setError("Sign in to review this movie"); return; }
    setSaving(true);
    try {
      if (editingId) await updateMovieReview(editingId, token, { rating, text });
      else await createMovieReview(movieId, token, { rating, text });
      setRating(0); setText(""); setEditingId(null); await load(1, false);
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
    await deleteMovieReview(reviewId, token); await load(1, false);
  }

  return (
    <section aria-labelledby="reviews-heading" style={{ padding: "40px 5% 80px" }}>
      <div className="glass-panel" style={{ padding: 28 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 32, marginBottom: 32, alignItems: "center" }}>
          <div>
            <h2 id="reviews-heading" style={{ fontSize: 28, marginBottom: 8 }}>Ratings & Reviews</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 24 }}>
              <strong>{average.toFixed(1)}</strong> <Star size={24} fill="#facc15" color="#facc15" style={{ display: "inline", verticalAlign: "sub" }} />
            </p>
            <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
              from {count} review{count === 1 ? "" : "s"}
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, minWidth: 200 }}>
            {[5, 4, 3, 2, 1].map((star) => {
              const starCount = distribution[star] || 0;
              const percentage = count > 0 ? (starCount / count) * 100 : 0;
              return (
                <div key={star} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ minWidth: 24, fontSize: 14 }}>{star}★</span>
                  <div style={{ flex: 1, height: 8, background: "var(--bg-elevated)", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{ width: `${percentage}%`, height: "100%", background: "#facc15" }} />
                  </div>
                  <span style={{ minWidth: 30, fontSize: 12, color: "var(--text-secondary)", textAlign: "right" }}>{starCount}</span>
                </div>
              );
            })}
          </div>
        </div>

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
        {loading && items.length === 0 ? <p>Loading reviews…</p> : items.length === 0 ? <p>No reviews yet. Be the first.</p> : (
          <>
            <div style={{ display: "grid", gap: 16 }}>
              {items.map((review) => (
                <article key={review.id} className="glass-panel" style={{ padding: 18 }}>
                  <div style={{ display: "flex", gap: 12, marginBottom: 12, alignItems: "center" }}>
                    {review.reviewer_avatar ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={review.reviewer_avatar} alt="" style={{ width: 40, height: 40, borderRadius: "50%" }} />
                    ) : (
                      <div style={{ width: 40, height: 40, borderRadius: "50%", background: "var(--bg-elevated)" }} />
                    )}
                    <div>
                      <strong style={{ display: "block" }}>{review.reviewer_name || "Anonymous User"}</strong>
                      <div aria-label={`${review.rating} out of 5 stars`} style={{ color: "#facc15", fontSize: 14 }}>{"★".repeat(review.rating)}{"☆".repeat(5-review.rating)}</div>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                    <div>
                      <p style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{review.text || "No written review."}</p>
                    </div>
                    {review.is_owner && <div style={{ display: "flex", gap: 8 }}>
                      <button type="button" aria-label="Edit review" onClick={() => startEdit(review)} className="btn btn-glass"><Pencil size={16}/></button>
                      <button type="button" aria-label="Delete review" onClick={() => void remove(review.id)} className="btn btn-glass"><Trash2 size={16}/></button>
                    </div>}
                  </div>
                </article>
              ))}
            </div>
            {hasMore && (
              <div style={{ display: "flex", justifyContent: "center", marginTop: 24 }}>
                <button className="btn btn-glass" onClick={() => load(page + 1, true)} disabled={loading}>
                  {loading ? "Loading..." : "Load More"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
