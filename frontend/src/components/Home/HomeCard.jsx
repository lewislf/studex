import { Card, Text, Group, Space } from '@mantine/core';
import styles from '../../styles/Home/Home.module.css'

/**
 * A customizable generic card subcomponent designed to render status items and metrics.
 * Supports side-by-side flexbox alignment containing labels, numerical values, and dynamic raw icons.
 */
export default function HomeCard({title, text, Icon, iconColor = 'orange'}) {
    return (
        <Card shadow="md" padding="xl" className={styles.card}>
            <Group justify="space-between" align="flex-start" wrap="nowrap">

                {/* Text */}
                <div style={{ flex: 1 }}>
                    <Text fw={500} size="lg">
                        {title}
                    </Text>
                    <Text mt="xs" c="dimmed" size="sm">
                        {text}
                    </Text>
                </div>

                {/* Icon */}
                {Icon && (
                    <>
                        <Space h='xl' />
                        <Icon
                            size={40}
                            color={iconColor}
                            style={{ minWidth: '30px', alignSelf: 'center' }}
                        />
                    </>
                )}

            </Group>
        </Card>
    );
}
