import { Stack, Title, Text, Button, Flex } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectsTitle renders the main header banner for the subjects view,
 * containing descriptions and the control gateway to add new subjects.
 */
export default function SubjectsTitle({ onAddClick }) {
    return (
        <Flex
            justify="space-between"
            align={{ base: 'flex-start', sm: 'center' }}
            direction={{ base: 'column', sm: 'row' }}
            gap="md"
            className={styles.titleSection}
        >
            {/* Title text labels */}
            <Stack gap={4}>
                <Title className={styles.pageTitle} order={1}>
                    Suas Matérias
                </Title>
                <Text className={styles.pageSubtitle}>
                    Cada disciplina é uma seção do seu fichário, com seus próprios resumos, mapas mentais e baralhos.
                </Text>
            </Stack>

            {/* Action button to create a new subject */}
            <Button
                leftSection={<IconPlus size={16} />}
                className={styles.addButton}
                onClick={() => onAddClick?.()}
            >
                Adicionar nova Matéria
            </Button>
        </Flex>
    );
}
