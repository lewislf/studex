import { useState } from 'react';
import { getAuthHeaders } from './useAuth';

/**
 * Custom hook to handle asynchronous multipart PDF uploads to a given API endpoint.
 * Manages loading, error, and success states natively.
 */
export function usePdfUpload(endpointUrl) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    // 207 means the document was indexed but some material failed to
    // generate or save (see document_routes.py upload_document). It's not a
    // full failure, but it's not a full success either.
    const [partial, setPartial] = useState(false);
    const [partialMessage, setPartialMessage] = useState(null);

    /**
     * Prepares binary files inside a FormData payload and dispatches the HTTP POST request.
     * @param {File} file - The raw binary file instance fetched from the Dropzone.
     * @param {Object} [options] - Target options for the uploaded material.
     * @param {string|number} [options.subjectId] - Target subject ID to associate the generated materials.
     * @param {string|number} [options.userId] - The user ID who owns the upload.
     * @param {string[]} [options.materials] - Subset of ['resumo', 'mapa_mental', 'flashcards']
     *   to generate. Omitted means "generate everything", matching the backend default when
     *   the `materials` form field is absent.
     */
    const uploadPdf = async (file, { subjectId, userId, materials } = {}) => {
        if (!file) return null;

        // Reset state cycles before starting a new request stream
        setLoading(true);
        setError(null);
        setSuccess(false);
        setPartial(false);
        setPartialMessage(null);

        const formData = new FormData();
        // 'file' represents the key expected by the backend
        formData.append('file', file);
        // Target subject - the backend associates generated materials with this subject ID
        if (subjectId !== undefined && subjectId !== null) {
            formData.append('subject_id', subjectId);
        }
        if (userId !== undefined && userId !== null) {
            formData.append('user_id', userId);
        }
        // Omitting `materials` tells the backend to generate all of them,
        // so only send it when the caller asked for a strict subset.
        if (Array.isArray(materials) && materials.length > 0) {
            formData.append('materials', materials.join(','));
        }

        try {
            // POST request
            const response = await fetch(endpointUrl, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData,
            });

            if (!response.ok) {
                const text = await response.text();
                console.error(text)
                throw new Error(`Upload failed with status: ${response.status}`);
            }

            const data = await response.json();

            if (response.status === 207) {
                // Indexed, but flashcards/resumo/mapa partially failed to
                // generate or save. Not a green success: surface it as a
                // partial success so the caller can warn the user instead
                // of quietly celebrating a lossy upload.
                setPartial(true);
                setPartialMessage(data.error || 'Alguns materiais não foram gerados ou salvos.');
            } else {
                setSuccess(true);
            }
            return data;
        } catch (err) {
            setError(err.message || 'Houve algum erro durante o Upload');
            return null;
        } finally {
            setLoading(false);
        }
    };

    return { uploadPdf, loading, error, success, partial, partialMessage };
}
