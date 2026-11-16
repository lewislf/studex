// trechos onde citações não devem ser mexidas: blocos de código, código inline e
// fórmulas (cifrão escapado, como em R\$, não abre fórmula)
const PROTEGIDO = /(```[\s\S]*?```|`[^`\n]*`|(?<!\\)\$\$[\s\S]+?(?<!\\)\$\$|(?<!\\)\$[^$\n]+?(?<!\\)\$)/g;

/**
 * Prepara a resposta do modelo para o Markdown: troca os delimitadores
 * \( \) e \[ \] por $ e $$ (o remark-math só entende cifrão), escapa "R$"
 * para não abrir fórmula, põe $$ em linhas próprias (senão o remark-math
 * desenha como fórmula inline) e transforma citações [1] ou [1, 2] em links
 * #cite-n, que o componente `a` desenha como selo.
 */
export function prepararMarkdown(text) {
    const comCifrao = String(text ?? '')
        .replace(/\\\[([\s\S]+?)\\\]/g, (_, m) => `$$${m}$$`)
        .replace(/\\\(([\s\S]+?)\\\)/g, (_, m) => `$${m}$`)
        .replace(/R\$/g, 'R\\$');

    return comCifrao
        .split(PROTEGIDO)
        .map((part, i) => {
            if (i % 2 === 1) {
                return part.startsWith('$$') ? `\n$$\n${part.slice(2, -2).trim()}\n$$\n` : part;
            }
            return part.replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g, (_, nums) =>
                nums.split(',').map((n) => `[${n.trim()}](#cite-${n.trim()})`).join('')
            );
        })
        .join('');
}
