import { useState, useCallback } from 'react';
import { parseSubjectsListMock } from '../utils/userHelpers';

const API_URL = import.meta.env.VITE_API_URL;

/**
 * Hook to list a user's subjects and create new subjects.
 * Used by the selection menu when uploading files and by the subjects dashboard page.
 *
 * @param {string|number} userId - Current user ID.
 */
export function useSubjects(userId) {
    const [subjects, setSubjects] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /** Fetches the user's existing subjects (GET /users/:userId/subjects). */
    const fetchSubjects = useCallback(async () => {
        setLoading(true);
        setError(null);

        if (userId === undefined || userId === null || userId === '') {
            setSubjects([]);
            setLoading(false);
            return;
        }

        try {
            // Busca as matérias reais do usuário. O parser enriquece com ícone/cor
            // do mock só como fallback visual, mas o id vem do banco (integer).
            const response = await fetch(`${API_URL}/users/${encodeURIComponent(userId)}/subjects`);
            if (!response.ok) {
                throw new Error(`Falha ao carregar matérias (status ${response.status})`);
            }
            const rawData = await response.json();
            setSubjects(parseSubjectsListMock(rawData));
        } catch (err) {
            setError(err.message || 'Erro ao carregar matérias');
            setSubjects([]);
        } finally {
            setLoading(false);
        }
    }, [userId]);

    /**
     * Creates a new subject (POST /subjects) and returns the generated ID.
     * @param {Object} params - Creation attributes.
     * @param {string} params.name - Title/Name of the subject.
     * @param {string} params.description - Optional description of the subject.
     * @param {string} [params.icon] - Icon key chosen for the subject.
     * @param {string} [params.color] - Color chosen for the subject.
     * @returns {Promise<number|null>} Created subject ID, or null on error.
     */
    const createSubject = useCallback(async ({ name, description, icon = 'book', color = '#4361ee' }) => {
        setError(null);

        try {
            const response = await fetch(`${API_URL}/users/${encodeURIComponent(userId)}/subjects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    name,
                    description,
                    domain: 0,
                    icon,
                    color,
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
