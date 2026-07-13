/**
 * Global constants and fallback configurations for Studex frontend.
 */

export const DEFAULT_SUBJECT_COLOR = '#4361ee';
export const DEFAULT_SUBJECT_ICON = 'book';

export const ICON_OPTIONS = [
    { name: 'book', label: 'Livro' },
    { name: 'globe', label: 'Redes/Globo' },
    { name: 'rocket', label: 'Foguete' },
    { name: 'user-teacher', label: 'Professor' },
    { name: 'users', label: 'Pessoas' },
    { name: 'database', label: 'Banco de Dados' },
    { name: 'calculator', label: 'Cálculo/Matemática' },
    { name: 'flask', label: 'Química/Ciência' },
    { name: 'code', label: 'Código/Programação' },
    { name: 'language', label: 'Idiomas' },
    { name: 'brain', label: 'Mente/Psicologia' },
    { name: 'palette', label: 'Artes/Design' },
    { name: 'history', label: 'História' },
    { name: 'microscope', label: 'Biologia/Ciências' },
    { name: 'heart', label: 'Saúde' },
    { name: 'scale', label: 'Direito/Justiça' },
];

export const COLOR_OPTIONS = [
    '#e63946', // Red
    '#ffb703', // Yellow
    '#fb8500', // Orange
    '#4caf50', // Leaf Green
    '#4361ee', // Blue
    '#2ec4b6', // Green
    '#4cc9f0', // Sky Blue
    '#7209b7', // Deep Purple
    '#9b5de5', // Purple
    '#ff70a6', // Soft Pink
    '#f72585', // Hot Pink
];

export const LINKS = [
    { link: '/', label: 'Home' },
    { link: '/revisoes', label: 'Revisões' },
    { link: '/materias', label: 'Matérias' },
    { link: '/estatisticas', label: 'Estatísticas' },
];

export const CREATION_OPTIONS = [
    {
        value: 'resumo',
        icon: 'file-text',
        title: 'Resumo',
        description: 'Estruturado, com tópicos e marcadores',
        color: 'blue',
    },
    {
        value: 'mapa_mental',
        icon: 'sitemap',
        title: 'Mapa Mental',
        description: 'Navegável, com visão',
        color: 'grape',
    },
    {
        value: 'flashcards',
        icon: 'cards',
        title: 'Flashcards',
        description: 'Revisão espaçada',
        color: 'orange',
    },
];

export const UPLOAD_PHASES = ['Criando resumo', 'Criando mapa mental', 'Criando flashcards'];

export const WEEKDAYS_UPPER = ['DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB'];
export const WEEKDAYS_TITLE = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
export const MONTHS_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
