import { useState } from 'react';

/**
 * Custom hook to handle asynchronous multipart PDF uploads to a given API endpoint.
 * Manages loading, error, and success states natively.
 */
export function usePdfUpload(endpointUrl) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    /**
     * Prepares binary files inside a FormData payload and dispatches the HTTP POST request.
     * @param {File} file - The raw binary file instance fetched from the Dropzone.
     */
    const uploadPdf = async (file) => {
        if (!file) return null;

        // Reset state cycles before starting a new request stream
        setLoading(true);
        setError(null);
        setSuccess(false);

        const formData = new FormData();
        // 'file' represents the key expected by the backend
        formData.append('file', file);

        try {
            // POST request
            const response = await fetch(endpointUrl, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed with status: ${response.status}`);
            }

            const data = await response.json();
            setSuccess(true);
            return data;
        } catch (err) {
            setError(err.message || 'Houve algum erro durante o Upload');
            return null;
        } finally {
            setLoading(false);
        }
    };

    return { uploadPdf, loading, error, success };
}
