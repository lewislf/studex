// Chamadas da API de chats (/users/:id/chats).

import { getAuthHeaders } from '../../hooks/useAuth';

const API_URL = import.meta.env.VITE_API_URL;

/**
 * Faz a requisição e devolve o JSON; em erro, lança Error com a mensagem do
 * backend (ex.: limite de perguntas, IA indisponível) e o status em err.status.
 */
async function request(path, { method = 'GET', body } = {}) {
    const res = await fetch(`${API_URL}${path}`, {
        method,
        headers: body ? { 'Content-Type': 'application/json', ...getAuthHeaders() } : getAuthHeaders(),
        body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => null);
    if (!res.ok) {
        const err = new Error(data?.error || `Falha na requisição (${res.status})`);
        err.status = res.status;
        throw err;
    }
    return data;
}

export function fetchChats(userId) {
    return request(`/users/${userId}/chats`);
}

export function createChat(userId, subjectId) {
    return request(`/users/${userId}/chats`, { method: 'POST', body: { subject_id: subjectId } });
}

/** O chat com o campo `mensagens` (histórico em ordem). */
export function fetchChat(userId, chatId) {
    return request(`/users/${userId}/chats/${chatId}`);
}

export function deleteChat(userId, chatId) {
    return request(`/users/${userId}/chats/${chatId}`, { method: 'DELETE' });
}

/** Envia a pergunta; devolve { answer, sources }. */
export function sendMessage(userId, chatId, question) {
    return request(`/users/${userId}/chats/${chatId}/messages`, { method: 'POST', body: { question } });
}
