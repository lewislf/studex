import { describe, it, expect } from 'vitest';
import { parseConteudo, stripMaterialSuffix, formatDate, deckTitle, deckDate } from '../components/SubjectDetail/api';

describe('SubjectDetail api helpers', () => {
    describe('parseConteudo', () => {
        it('parses a valid JSON string', () => {
            expect(parseConteudo('{"a":1,"b":"x"}')).toEqual({ a: 1, b: 'x' });
        });

        it('returns the value as-is when already an object', () => {
            const obj = { a: 1 };
            expect(parseConteudo(obj)).toBe(obj);
        });

        it('returns null for invalid JSON', () => {
            expect(parseConteudo('{invalid json')).toBeNull();
        });

        it('returns null for missing input', () => {
            expect(parseConteudo(null)).toBeNull();
            expect(parseConteudo(undefined)).toBeNull();
            expect(parseConteudo('')).toBeNull();
        });
    });

    describe('stripMaterialSuffix', () => {
        it('strips a simple known suffix', () => {
            expect(stripMaterialSuffix('Fotossíntese — Mapa Mental de Estudo')).toBe('Fotossíntese');
            expect(stripMaterialSuffix('Fotossíntese — Flashcards')).toBe('Fotossíntese');
        });

        it('strips a duplicated suffix', () => {
            expect(stripMaterialSuffix('Fotossíntese — Mapa Mental de Estudo — Mapa Mental de Estudo')).toBe('Fotossíntese');
        });

        it('leaves a title without a known suffix untouched', () => {
            expect(stripMaterialSuffix('Fotossíntese')).toBe('Fotossíntese');
        });

        it('returns an empty string for missing input', () => {
            expect(stripMaterialSuffix(null)).toBe('');
            expect(stripMaterialSuffix('')).toBe('');
        });
    });

    describe('formatDate', () => {
        it('formats a plain date', () => {
            expect(formatDate('2026-07-08')).toBe('08/07/2026');
        });

        it('formats a full ISO datetime with time', () => {
            expect(formatDate('2026-07-08T03:52:41')).toBe('08/07/2026 às 03:52');
        });

        it('returns an empty string for missing input', () => {
            expect(formatDate(null)).toBe('');
            expect(formatDate('')).toBe('');
        });

        it('returns the raw string unchanged when it has no date-like segments', () => {
            expect(formatDate('garbage')).toBe('garbage');
        });
    });

    describe('deckTitle', () => {
        it('prefers titulo, stripping known suffixes', () => {
            expect(deckTitle({ titulo: 'Baralho — Flashcards' })).toBe('Baralho');
        });

        it('falls back to subtitle when titulo is missing', () => {
            expect(deckTitle({ subtitle: 'Revisão de Física' })).toBe('Revisão de Física');
        });

        it('falls back to a default label when nothing is set', () => {
            expect(deckTitle({})).toBe('Baralho sem título');
            expect(deckTitle(null)).toBe('Baralho sem título');
        });
    });

    describe('deckDate', () => {
        it('prefers creation_date', () => {
            expect(deckDate({ creation_date: '2026-01-01', date: '2025-01-01' })).toBe('2026-01-01');
        });

        it('falls back to date when creation_date is missing', () => {
            expect(deckDate({ date: '2025-01-01' })).toBe('2025-01-01');
        });

        it('returns an empty string when neither field is set', () => {
            expect(deckDate({})).toBe('');
            expect(deckDate(null)).toBe('');
        });
    });
});
