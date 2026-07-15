import {
    IconGlobe,
    IconRocket,
    IconSchool,
    IconUsers,
    IconDatabase,
    IconBook,
    IconCalculator,
    IconFlask,
    IconCode,
    IconLanguage,
    IconBrain,
    IconPalette,
    IconHistory,
    IconMicroscope,
    IconHeart,
    IconScale,
    IconAtom,
    IconFlame,
    IconCards,
    IconSitemap,
    IconFileText,
    IconSum
} from '@tabler/icons-react';

/**
 * Reusable icon component that maps string identifiers to Icon components.
 *
 * @param {Object} props
 * @param {string} props.name - The identifier name of the icon.
 * @param {number} [props.size=24] - Size of the icon in pixels.
 * @param {string} [props.color] - Custom CSS color value.
 */
export default function SubjectIcon({ name, size = 24, color, ...props }) {
    switch (name) {
        case 'sigma':
            return <IconSum size={size} color={color} {...props} />;
        case 'atom':
            return <IconAtom size={size} color={color} {...props} />;
        case 'globe':
            return <IconGlobe size={size} color={color} {...props} />;
        case 'rocket':
            return <IconRocket size={size} color={color} {...props} />;
        case 'user-teacher':
            return <IconSchool size={size} color={color} {...props} />;
        case 'users':
            return <IconUsers size={size} color={color} {...props} />;
        case 'database':
            return <IconDatabase size={size} color={color} {...props} />;
        case 'calculator':
            return <IconCalculator size={size} color={color} {...props} />;
        case 'flask':
            return <IconFlask size={size} color={color} {...props} />;
        case 'code':
            return <IconCode size={size} color={color} {...props} />;
        case 'language':
            return <IconLanguage size={size} color={color} {...props} />;
        case 'brain':
            return <IconBrain size={size} color={color} {...props} />;
        case 'palette':
            return <IconPalette size={size} color={color} {...props} />;
        case 'history':
            return <IconHistory size={size} color={color} {...props} />;
        case 'microscope':
            return <IconMicroscope size={size} color={color} {...props} />;
        case 'heart':
            return <IconHeart size={size} color={color} {...props} />;
        case 'scale':
            return <IconScale size={size} color={color} {...props} />;
        case 'flame':
            return <IconFlame size={size} color={color} {...props} />;
        case 'cards':
            return <IconCards size={size} color={color} {...props} />;
        case 'sitemap':
            return <IconSitemap size={size} color={color} {...props} />;
        case 'file-text':
            return <IconFileText size={size} color={color} {...props} />;
        default:
            return <IconBook size={size} color={color} {...props} />;
    }
}
