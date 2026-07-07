import { Container } from "@mantine/core";
import styles from '../../styles/Revisions/Revisions.module.css';
import dailyReviewsMock from '../../config/dailyReviewsMock.json';
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
    // Parse structured review metrics directly from local configuration mocks using pre-defined parser
    const data = parseDailyReviews(dailyReviewsMock);

    return (
        <Container size="xl" className={styles.container}>
            {/* Page title and description banner */}
            <RevisionsTitle />

            {/* Split pending details block */}
            <RevisionsSummary summary={data.summary} />

            {/* Decks filtering tab list grid */}
            <RevisionsDeckList decksToday={data.decksToday} />

            {/* Weekly forecast tracker */}
            <RevisionsProjection projection={data.next7DaysProjection} />
        </Container>
    );
}
