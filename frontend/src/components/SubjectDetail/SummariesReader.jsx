import { Box, Text, Title, Badge } from '@mantine/core';
import { IconCalendar } from '@tabler/icons-react';
import styles from '../../styles/SubjectDetail/Summaries.module.css';
import { formatDate } from './api.js';

/**
 * SummariesReader renders the full content of a single summary: title,
 * creation date, key-topic badges, and the body text split into paragraphs.
 *
 * @param {Object} props
 * @param {Object} props.summary - Summary record returned by the API.
 */
export default function SummariesReader({ summary }) {
    if (!summary) return null;

    const topicos = summary.conteudo?.topicos_chave ?? [];
    const texto = summary.conteudo?.texto ?? '';
    const paragraphs = texto.split('\n\n').filter((p) => p.trim() !== '');

    return (
        <Box className={styles.reader}>
            <Title order={2} className={styles.readerTitle}>{summary.titulo}</Title>

            <Box className={styles.readerDate}>
                <IconCalendar size={16} />
                <Text component="span" size="sm">{formatDate(summary.creation_date)}</Text>
            </Box>

            {topicos.length > 0 && (
                <Box className={styles.badgeRow}>
                    {topicos.map((topico, index) => (
                        <Badge key={index} variant="light" color="blue" radius="sm">
                            {topico}
                        </Badge>
                    ))}
                </Box>
            )}

            <Box>
                {paragraphs.map((paragraph, index) => (
                    <Text key={index} className={styles.paragraph} mb="md">
                        {paragraph}
                    </Text>
                ))}
            </Box>
        </Box>
    );
}
