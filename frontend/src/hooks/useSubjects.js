import { useState, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL;

/**
 * Hook para listar as matérias de um usuário e criar novas matérias.
 * Usado pelo menu de seleção que aparece ao enviar um arquivo.
 */
export function useSubjects(userId) {
    const [subjects, setSubjects] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /** Busca as matérias existentes do usuário (GET /subjects?user_id=...). */
    const fetchSubjects = useCallback(async () => {
        if (userId === undefined || userId === null || userId === '') return;

        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/subjects?user_id=${encodeURIComponent(userId)}`);

            if (!response.ok) {
                throw new Error(`Falha ao carregar matérias (status ${response.status})`);
            }

            setSubjects(await response.json());
        } catch (err) {
            setError(err.message || 'Erro ao carregar matérias');
        } finally {
            setLoading(false);
        }
    }, [userId]);

    /**
     * Cria uma nova matéria (POST /subjects) e devolve o id gerado.
     * @returns {Promise<number|null>} id da matéria criada, ou null em caso de erro.
     */
    const createSubject = useCallback(async ({ name, description }) => {
        setError(null);

        try {
            const response = await fetch(`${API_URL}/subjects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    name,
                    description,
                    domain: 0,
                    date: new Date().toISOString().slice(0, 10),
                }),
            });

            if (!response.ok) {
                throw new Error(`Falha ao criar matéria (status ${response.status})`);
            }

            const data = await response.json();
            return data.id;
        } catch (err) {
            setError(err.message || 'Erro ao criar matéria');
            return null;
        }
    }, [userId]);

    return { subjects, loading, error, fetchSubjects, createSubject };
}
