import { Container, Stack } from "@mantine/core";
import { useOutletContext } from "react-router";
import { useState, useEffect } from "react";
import styles from '../../styles/Subjects/Subjects.module.css';
import { useSubjects } from '../../hooks/useSubjects';
import SubjectPickerModal from '../Common/SubjectPickerModal';
import SubjectsTitle from "./SubjectsTitle.jsx";
import SubjectsGrid from "./SubjectsGrid.jsx";

/**
 * Parent view container for the application subjects (Matérias) route dashboard entry point.
 * Integrates listing retrieval from backend and handles creation modals.
 */
export default function Subjects() {
    // Consume user context from layout outlet
    const user = useOutletContext();
    const userId = user?.id;

    // Use useSubjects hook for fetching and creating subjects
    const { subjects, fetchSubjects } = useSubjects(userId);
    const [modalOpened, setModalOpened] = useState(false);

    // Fetch list on mount or user changes
    useEffect(() => {
        if (userId) {
            fetchSubjects();
        }
    }, [userId, fetchSubjects]);

    // Handle re-fetching after creating a new subject from the picker modal
    const handleSubjectCreateConfirm = async () => {
        fetchSubjects();
    };

    return (
        <Container size="xl" className={styles.container}>
            <Stack gap="sm">
                {/* Greeting banner with creation click handler */}
                <SubjectsTitle onAddClick={() => setModalOpened(true)} />

                {/* Grid displaying subject cards */}
                <SubjectsGrid subjects={subjects} />
            </Stack>

            {/* Creation Picker Modal in onlyCreate mode */}
            <SubjectPickerModal
                opened={modalOpened}
                onClose={() => setModalOpened(false)}
                userId={userId}
                onConfirm={handleSubjectCreateConfirm}
                onlyCreate
            />
        </Container>
    );
}
