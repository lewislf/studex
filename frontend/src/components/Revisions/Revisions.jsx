import { Container } from "@mantine/core";
import styles from '../../styles/Revisions/Revisions.module.css';
import { parseDailyReviews } from '../../utils/userHelpers.js';
import RevisionsTitle from "./RevisionsTitle";
import RevisionsSummary from "./RevisionsSummary";
import RevisionsDeckList from "./RevisionsDeckList";
import RevisionsProjection from "./RevisionsProjection";

/**
 * Parent view container for the application reviews (Revisões) route entry point.
 * Orchestrates subcomponents representing daily schedules, metrics splits, and forecast projections.
 */
export default function Revisions() {
    // No reviews endpoint on the backend yet: a new account starts with no queue.
    // Empty structure (zeroed queues, empty lists) until the route exists.
    const data = parseDailyReviews({});

    return (
        <Container size="xl" className={styles.container}>
            {/* Page title and description banner */}
            <RevisionsTitle />

            {/* Decks filtering tab list grid */}
            <RevisionsDeckList decksToday={data.decksToday} />

            {/* Split pending details block */}
            <RevisionsSummary summary={data.summary} />

            {/* Weekly forecast tracker */}
            <RevisionsProjection projection={data.next7DaysProjection} />
        </Container>
    );
}
