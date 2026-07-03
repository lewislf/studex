import { useRef } from 'react';
import { IconCloudUpload, IconX, IconCheck } from '@tabler/icons-react';
import { Group, Text, useMantineTheme, Loader } from '@mantine/core';
import { Dropzone, MIME_TYPES } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import { usePdfUpload } from '../../hooks/usePdfUpload';
import classes from '../../styles/Mantine/PdfDropZone.module.css';

export default function HomePdfDropzone() {
    const theme = useMantineTheme();

    // trigger the file input dialog
    const openRef = useRef(null);

    // Network logic
    const { uploadPdf, loading, error, success } = usePdfUpload('api-url');

    /**
     * Event handler triggered whenever a file satisfies the constraint filters.
     * @param {File[]} files - Validated array of native JS file entries.
     */
    async function handleDrop(files) {
        if (files.length > 0) {
            const file = files[0];

            // Logs
            console.log('--- File Selected ---');
            console.log('File Name:', file.name);
            console.log('File Size:', (file.size / (1024 * 1024)).toFixed(2) + ' MB');

            // Dispatching dynamic multipart payload to the target backend cluster
            const result = await uploadPdf(file);

            if (result) {
                console.log('Server response:', result);

                // Toast notification via Mantine standard overlay
                notifications.show({
                    title: 'Upload concluído',
                    message: `O arquivo "${file.name}" foi processado com sucesso!`,
                    color: 'green',
                    icon: <IconCheck size={16} />,
                    autoClose: 4000,
                });
            } else {
                // Toast notification if the hook caught an error
                notifications.show({
                    title: 'Falha no upload',
                    message: 'Não foi possível enviar o documento. Tente novamente.',
                    color: 'red',
                    icon: <IconX size={16} />,
                    autoClose: 5000,
                });
            }
        }
    }

    /**
     * Catch-all fallback interceptor handling runtime drag/drop validation rejections
     * @param {Object[]} fileRejections - Array mapping rejection events and failure codes
     */
    function handleReject(fileRejections) {
        console.error('File rejected:', fileRejections);

        // Map contextual feedback text matching the dynamic validation error code
        const reason = fileRejections[0]?.errors[0]?.code === 'file-too-large' 
            ? 'O arquivo excede o limite de 50MB.' 
            : 'Formato inválido. Apenas arquivos .pdf são aceitos.';

        notifications.show({
            title: 'Arquivo rejeitado',
            message: reason,
            color: 'red',
            icon: <IconX size={16} />,
        });
    }

    return (
        <div className={classes.wrapper}>
            <Dropzone
                openRef={openRef}
                onDrop={handleDrop} 
                onReject={handleReject}
                className={classes.dropzone}
                radius="md"
                accept={[MIME_TYPES.pdf]}
                maxSize={50 * 1024 ** 2} // 50MB maximum threshold limit
                loading={loading}        // Displays native Mantine loading background overlay during uploads
                aria-label="Upload PDF"
            >
                <div style={{ pointerEvents: 'none' }}>
                    <Group justify="center">
                        {loading ? (
                            <Loader size={40} />
                        ) : (
                                <>
                                    <Dropzone.Accept>
                                        <IconCloudUpload size={40} color={theme.colors.blue[6]} stroke={1.5} />
                                    </Dropzone.Accept>
                                    <Dropzone.Reject>
                                        <IconX size={40} color={theme.colors.red[6]} stroke={1.5} />
                                    </Dropzone.Reject>
                                    <Dropzone.Idle>
                                        {/* Swap upload icon for a checkmark once successful */}
                                        {success ? (
                                            <IconCheck size={40} color={theme.colors.green[6]} stroke={1.5} />
                                        ) : (
                                                <IconCloudUpload size={40} stroke={1.5} className={classes.icon} />
                                            )}
                                    </Dropzone.Idle>
                                </>
                            )}
                    </Group>

                    <Text ta="center" fw={600} fz="sm" mt="sm">
                        <Dropzone.Accept>Solte o arquivo aqui</Dropzone.Accept>
                        <Dropzone.Reject>Apenas arquivos PDF menores que 50MB</Dropzone.Reject>
                        <Dropzone.Idle>
                            {success ? 'Arquivo enviado com sucesso!' : 'Clique ou arraste seu PDF aqui'}
                        </Dropzone.Idle>
                    </Text>

                    {/* Dynamic color swap for the description layout depending on network state */}
                    <Text 
                        className={classes.description} 
                        c={error ? 'red.6' : success ? 'green.6' : 'dimmed'}
                        fw={error || success ? 500 : 400}
                    >
                        {error ? `Erro: ${error}` : 'Tamanho máximo suportado: 50MB'}
                    </Text>
                </div>
            </Dropzone>
        </div>
    );
}
