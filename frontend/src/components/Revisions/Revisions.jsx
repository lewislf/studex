import { useEffect, useState } from "react";
import { Container } from "@mantine/core";
import { useOutletContext } from "react-router";
import styles from '../../styles/Revisions/Revisions.module.css';
import { parseDailyReviews } from '../../utils/userHelpers.js';
import { getAuthHeaders } from '../../hooks/useAuth.js';
import RevisionsTitle from "./RevisionsTitle";
import RevisionsSummary from "./RevisionsSummary";
import RevisionsDeckList from "./RevisionsDeckList";
import RevisionsProjection from "./RevisionsProjection";

const API_URL = import.meta.env.VITE_API_URL;

export default function Revisions() {
    const { refreshUser: _r, ...user } = useOutletContext();
    const [data, setData] = useState(() => parseDailyReviews({}));

    useEffect(() => {
        if (!user?.id) return;

        // Prevents setState after unmount if the user navigates away mid-fetch.
        let cancelled = false;

        async function fetchDecks() {
            try {
                // uma requisição só: todos os baralhos já com nome, ícone e cor da matéria
                const res = await fetch(`${API_URL}/users/${user.id}/decks`, { headers: getAuthHeaders() });
                if (!res.ok) return;
                const allDecks = await res.json();

                if (cancelled) return;

                // O baralho tem sua própria cor fixa no backend (não a da
                // matéria): usa o ícone/cor reais da matéria.
                const decksToday = allDecks.map(d => {
                    return {
                        id: d.id,
                        subject_id: d.subject_id,
                        subject_name: d.subject_name,
                        subtitle: d.subtitle || '',
                        icon: d.subject_icon,
                        color: d.subject_color,
                        new: d.new ?? 0,
                        learning: d.learning ?? 0,
                        review: d.review ?? 0,
                        total_cards: d.total_cards ?? (d.new ?? 0) + (d.learning ?? 0) + (d.review ?? 0),
                    };
                });

                const totalNew = decksToday.reduce((s, d) => s + d.new, 0);
                const totalLearning = decksToday.reduce((s, d) => s + d.learning, 0);
                const totalReview = decksToday.reduce((s, d) => s + d.review, 0);
                const totalPending = totalNew + totalLearning + totalReview;

                if (cancelled) return;

                setData(parseDailyReviews({
                    decks_today: decksToday,
                    summary: {
                        total_pending: totalPending,
                        estimated_time_minutes: Math.ceil(totalPending * 0.5),
                        split: { new: totalNew, learning: totalLearning, review: totalReview },
                    },
                    next_7_days_projection: [],
                }));
            } catch {
                // network hiccup fetching decks: keep previous data instead of crashing the page
            }
        }

        fetchDecks();
        return () => { cancelled = true; };
    }, [user?.id]);

    return (
        <Container size="xl" className={styles.container}>
            <RevisionsTitle totalPending={data.summary.totalPending} />
            <RevisionsDeckList decksToday={data.decksToday} />
            <RevisionsSummary summary={data.summary} />
            <RevisionsProjection projection={data.next7DaysProjection} />
        </Container>
    );
}
