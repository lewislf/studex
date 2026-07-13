import { useEffect, useRef, useState } from 'react';
import { useOutletContext } from 'react-router';
import { IconCloudUpload, IconX, IconCheck, IconAlertTriangle } from '@tabler/icons-react';
import { Group, Text, useMantineTheme } from '@mantine/core';
import { Dropzone, MIME_TYPES } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import { usePdfUpload } from '../../hooks/usePdfUpload';
import SubjectPickerModal from '../Common/SubjectPickerModal';
import HomeUploadProgress from './HomeUploadProgress';
import classes from '../../styles/Mantine/PdfDropZone.module.css';

/**
 * @param {Set<string>} [selectedMaterials] - Values from CREATION_OPTIONS (resumo,
 *   mapa_mental, flashcards) the user picked in HomeCreationGrid. Drives both what
 *   gets sent to the backend and which phases the progress checklist shows.
 */
export default function HomePdfDropzone({ selectedMaterials }) {
    const theme = useMantineTheme();

    // Current user (provided by Outlet context in App.jsx)
    const { refreshUser, ...user } = useOutletContext();
    const userId = user?.id;

    // trigger the file input dialog
    const openRef = useRef(null);

    // Uploads can take minutes; if the user navigates away before it
    // finishes, handleSubjectConfirm must not touch state after unmount.
    const isMountedRef = useRef(true);
    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    // Pending file awaiting subject selection
    const [pendingFile, setPendingFile] = useState(null);
    const [modalOpened, setModalOpened] = useState(false);

    // Network logic
    const { uploadPdf, loading, error, success } = usePdfUpload(`${import.meta.env.VITE_API_URL}/users/${encodeURIComponent(userId)}/documents`);

    // Real (not simulated) per-phase progress: polled from the backend while
    // an upload is in flight, so HomeUploadProgress can show which materials
    // have actually finished, not a timed guess.
    const [uploadProgress, setUploadProgress] = useState(null);

    // The hook's own `loading` flips to false the instant the HTTP request
    // resolves, which can race ahead of the last poll (progress is also
    // cleared server-side the moment the request ends), so the checklist
    // could disappear without ever showing its final state. `holdCompletion`
    // keeps the panel up a bit longer, showing the REAL final state (derived
    // from the materials the response actually returned, not a guess).
    const [holdCompletion, setHoldCompletion] = useState(false);
    const [displayFileName, setDisplayFileName] = useState(null);
    // Snapshot of what was selected when the upload started: the checklist
    // must keep showing exactly those phases even if the user toggles the
    // cards above while the upload is still in flight.
    const [activePhases, setActivePhases] = useState(null);
    const showProgressPanel = loading || holdCompletion;

    useEffect(() => {
        // Nothing to poll: leave uploadProgress as-is and clear it only when
        // an in-flight poll loop actually stops (see cleanup below), instead
        // of setting state synchronously here.
        if (!loading || !userId) return;

        let cancelled = false;
        const API_URL = import.meta.env.VITE_API_URL;

        async function poll() {
            try {
                const res = await fetch(`${API_URL}/users/${encodeURIComponent(userId)}/documents/progress`);
                if (!res.ok || cancelled) return;
                const data = await res.json();
                setUploadProgress(data.active ? data : null);
            } catch {
                // rede instável durante o polling não deve derrubar a tela de progresso
            }
        }

        poll();
        const id = setInterval(poll, 1500);
        return () => {
            cancelled = true;
            clearInterval(id);
            setUploadProgress(null);
        };
    }, [loading, userId]);

    /**
     * On file drop, do not upload directly: open a menu for the user
     * to choose or create a subject where artifacts will be saved.
     * @param {File[]} files - Validated array of native JS file entries.
     */
    function handleDrop(files) {
        if (files.length === 0) return;

        // Nothing selected in the "Criar a partir de um material" grid: there's
        // nothing to generate, so stop before even asking which subject to use.
        if (!selectedMaterials || selectedMaterials.size === 0) {
            notifications.show({
                title: 'Nenhum material selecionado',
                message: 'Selecione ao menos um tipo de material acima antes de enviar o arquivo.',
                color: 'orange',
                icon: <IconAlertTriangle size={16} />,
            });
            return;
        }

        setPendingFile(files[0]);
        setModalOpened(true);
    }

    /**
     * Invoked when the user confirms the subject selection in the menu.
     * @param {string|number} subjectId - Chosen subject ID (either new or existing).
     */
    async function handleSubjectConfirm(subjectId) {
        setModalOpened(false);

        const file = pendingFile;
        if (!file) return;

        setDisplayFileName(file.name);
        setHoldCompletion(true);

        const materials = selectedMaterials ? Array.from(selectedMaterials) : undefined;
        setActivePhases(selectedMaterials ? new Set(selectedMaterials) : null);
        const result = await uploadPdf(file, { subjectId, userId, materials });
        // Upload can take minutes; the user may have navigated away by now.
        if (isMountedRef.current) setPendingFile(null);

        if (result) {
            // Estado final real, tirado dos materiais que a resposta de fato
            // trouxe (não um chute): se o mapa mental foi omitido (ex: sem
            // entidades suficientes), o checklist reflete isso corretamente.
            const tipos = new Set((result.materiais || []).map((m) => m.tipo));
            if (isMountedRef.current) {
                setUploadProgress({
                    resumo: tipos.has('resumo'),
                    mapa_mental: tipos.has('mapa_mental'),
                    flashcards: tipos.has('baralho'),
                });
            }
            await refreshUser();
            // Segura o checklist completo visível um instante antes de
            // trocar pra tela de sucesso, senão a troca é instantânea demais
            // pro usuário perceber que tudo terminou.
            await new Promise((resolve) => setTimeout(resolve, 2000));

            // Backend answers 207 (present as an `error` field even though
            // uploadPdf still returns the parsed body) when the document was
            // indexed but some material failed to generate or save. That's
            // not a full success: warn instead of showing the green toast.
            if (result.error) {
                notifications.show({
                    title: 'Upload concluído com falhas parciais',
                    message: `O arquivo "${file.name}" foi processado, mas: ${result.error}`,
                    color: 'orange',
                    icon: <IconAlertTriangle size={16} />,
                    autoClose: 6000,
                });
            } else {
                notifications.show({
                    title: 'Upload concluído',
                    message: `O arquivo "${file.name}" foi processado e salvo na matéria!`,
                    color: 'green',
                    icon: <IconCheck size={16} />,
                    autoClose: 4000,
                });
            }
        } else {
            notifications.show({
                title: 'Falha no upload',
                message: 'Não foi possível enviar o documento. Tente novamente.',
                color: 'red',
                icon: <IconX size={16} />,
                autoClose: 5000,
            });
        }

        if (isMountedRef.current) {
            setHoldCompletion(false);
            setUploadProgress(null);
            setDisplayFileName(null);
            setActivePhases(null);
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

            {showProgressPanel ? (
                // During processing (and briefly after, to show the final
                // state), the block is swapped for the progress tracker
                <div className={classes.dropzone}>
                    <HomeUploadProgress
                        fileName={displayFileName || pendingFile?.name}
                        progress={uploadProgress}
                        phases={activePhases}
                    />
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
