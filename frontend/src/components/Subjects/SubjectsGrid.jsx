import { SimpleGrid } from "@mantine/core";
import SubjectCard from "./SubjectCard";

/**
 * SubjectsGrid renders the responsive grid layout presenting all subject card elements.
 */
export default function SubjectsGrid({ subjects }) {
    return (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
            {subjects.map((subject) => (
                <SubjectCard key={subject.id} subject={subject} />
            ))}
        </SimpleGrid>
    );
}
