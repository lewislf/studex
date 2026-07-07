import { Box } from "@mantine/core";
import styles from '../../styles/Subjects/Subjects.module.css';
import SubjectCardHeader from "./SubjectCardHeader";
import SubjectCardCounters from "./SubjectCardCounters";
import SubjectCardMastery from "./SubjectCardMastery";
import SubjectCardFooter from "./SubjectCardFooter";

/**
 * SubjectCard represents a single course subject item, including status indicators,
 * topic descriptions, mastery percentage progress, and queue statistics.
 */
export default function SubjectCard({ subject }) {
    return (
        <Box className={styles.subjectCard}>
            <Box
                className={styles.cardStripe}
                style={{ backgroundColor: subject.color }}
            />

            {/* Main card contents container */}
            <Box className={styles.cardContent}>
                {/* Header: Title, Icon, Topics */}
                <SubjectCardHeader
                    icon={subject.icon}
                    color={subject.color}
                    title={subject.title}
                    totalTopics={subject.totalTopics}
                />

                {/* Badges: summaries, mind maps, and flashcards */}
                <SubjectCardCounters counters={subject.counters} />

                {/* Progress: mastery percentage tracker */}
                <SubjectCardMastery
                    masteryPercentage={subject.masteryPercentage}
                    color={subject.color}
                />

                {/* Footer: dot indicator, pending, open link */}
                <SubjectCardFooter
                    pendingInQueue={subject.pendingInQueue}
                    color={subject.color}
                />
            </Box>
        </Box>
    );
}
