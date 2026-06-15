import styles from './Button.module.css';

/**
 * @typedef {Object} ButtonProps
 * @property {string} label - The text to show inside the button.
 * @property {'primary' | 'secondary'} [variant='primary'] - The visual style of the button.
 * @property {function} onClick - The function called when the button is clicked.
 */

/**
 * A reusable custom button component.
 * 
 * @example
 * <Button label="Click Me" variant="primary" onClick={() => alert('Hi!')} />
 * 
 * @param {ButtonProps} props - The properties passed to the component.
 * @returns {JSX.Element} The rendered HTML button element.
 */
export const Button = ({ label, variant = 'primary', onClick }) => {
    const buttonClass = `${styles.btn} ${styles[variant]}`;

    return (
        <button onClick={onClick} className={buttonClass}>
            {label}
        </button>
    );
};
