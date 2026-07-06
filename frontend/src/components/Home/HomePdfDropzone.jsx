import { useRef, useState } from 'react';
import { useOutletContext } from 'react-router';
import { IconCloudUpload, IconX, IconCheck } from '@tabler/icons-react';
import { Group, Text, useMantineTheme } from '@mantine/core';
import { Dropzone, MIME_TYPES } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import { usePdfUpload } from '../../hooks/usePdfUpload';
import SubjectPickerModal from './SubjectPickerModal';
import UploadProgress from './UploadProgress';
import classes from '../../styles/Mantine/PdfDropZone.module.css';

export default function HomePdfDropzone() {
    const theme = useMantineTheme();

    // Current user (provided by Outlet context in App.jsx)
    const user = useOutletContext();
    const userId = user?.id;

    // trigger the file input dialog
    const openRef = useRef(null);

    // Pending file awaiting subject selection
    const [pendingFile, setPendingFile] = useState(null);
    const [modalOpened, setModalOpened] = useState(false);

    // Network logic
    const { uploadPdf, loading, error, success } = usePdfUpload(`${import.meta.env.VITE_API_URL}/documents`);

    /**
     * On file drop, do not upload directly: open a menu for the user
     * to choose or create a subject where artifacts will be saved.
     * @param {File[]} files - Validated array of native JS file entries.
     */
    function handleDrop(files) {
        if (files.length > 0) {
            setPendingFile(files[0]);
            setModalOpened(true);
        }
    }

    /**
     * Invoked when the user confirms the subject selection in the menu.
     * @param {string|number} subjectId - Chosen subject ID (either new or existing).
     */
    async function handleSubjectConfirm(subjectId) {
        setModalOpened(false);

        const file = pendingFile;
        if (!file) return;

        const result = await uploadPdf(file, { subjectId, userId });
        setPendingFile(null);

        if (result) {
            notifications.show({
                title: 'Upload concluído',
                message: `O arquivo "${file.name}" foi processado e salvo na matéria!`,
                color: 'green',
                icon: <IconCheck size={16} />,
                autoClose: 4000,
            });
        } else {
            notifications.show({
                title: 'Falha no upload',
                message: 'Não foi possível enviar o documento. Tente novamente.',
                color: 'red',
                icon: <IconX size={16} />,
                autoClose: 5000,
            });
        }
    }

    function handleModalClose() {
        setModalOpened(false);
        setPendingFile(null);
    }

    /**
     * Catch-all fallback interceptor handling drag/drop validation rejections.
     * @param {Object[]} fileRejections - Array mapping rejection events and failure codes.
     */
    function handleReject(fileRejections) {
        console.error('File rejected:', fileRejections);

        // Map contextual feedback text matching the dynamic validation error code
        const reason = fileRejections[0]?.errors[0]?.code === 'file-too-large' 
            ? 'O arquivo excede o limite de 250MB.'
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
            <SubjectPickerModal
                opened={modalOpened}
                onClose={handleModalClose}
                userId={userId}
                fileName={pendingFile?.name}
                onConfirm={handleSubjectConfirm}
            />

            {loading ? (
                // During processing, the block is swapped for a three-phase progress tracker
                <div className={classes.dropzone}>
                    <UploadProgress fileName={pendingFile?.name} />
                </div>
            ) : (
                <Dropzone
                    openRef={openRef}
                    onDrop={handleDrop}
                    onReject={handleReject}
                    className={classes.dropzone}
                    radius="md"
                    accept={[MIME_TYPES.pdf]}
                    maxSize={250 * 1024 ** 2} // Updated threshold constraint limit to 250MB
                    aria-label="Upload PDF"
                >
                    <div style={{ pointerEvents: 'none' }}>
                        <Group justify="center">
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
            )}
        </div>
    );
}
