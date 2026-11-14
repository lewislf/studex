import { useState } from 'react';
import { useNavigate } from 'react-router';
import { upperFirst, useToggle } from '@mantine/hooks';
import {
    Anchor,
    Button,
    Checkbox,
    Divider,
    Group,
    Paper,
    PasswordInput,
    Stack,
    Text,
    TextInput,
    Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconBrandGoogle, IconBrandGithub } from '@tabler/icons-react';
import { useAuth } from '../../hooks/useAuth';
import logo from '../../assets/logo.png';
import classes from '../../styles/Auth/Auth.module.css';

const EMAIL_REGEX = /^\S+@\S+$/;

/**
 * Login/Register screen following Mantine UI's first "Authentication form"
 * component. Toggles between sign in and sign up in the same card and talks
 * to the backend API (POST /users and POST /users/login).
 */
export default function Auth() {
    const navigate = useNavigate();
    const { register, login, loading, error } = useAuth();

    // Toggles the form mode: sign in vs sign up
    const [type, toggle] = useToggle(['login', 'register']);

    const [values, setValues] = useState({ name: '', email: '', password: '', terms: true });
    const [fieldErrors, setFieldErrors] = useState({});

    function setField(field, value) {
        setValues((prev) => ({ ...prev, [field]: value }));
    }

    /**
     * Local validation before firing the request.
     */
    function validate() {
        const errors = {};

        if (!EMAIL_REGEX.test(values.email)) {
            errors.email = 'Email inválido';
        }

        // Cadastro: mesmas regras do backend (8 a 128). Login: só exige senha
        // preenchida, pois contas antigas podem ter senhas curtas.
        if (type === 'register') {
            if (values.password.length < 8) {
                errors.password = 'A senha deve ter ao menos 8 caracteres';
            } else if (values.password.length > 128) {
                errors.password = 'A senha deve ter no máximo 128 caracteres';
            }
        } else if (values.password.length === 0) {
            errors.password = 'Informe sua senha';
        }

        if (type === 'register' && values.name.trim().length === 0) {
            errors.name = 'Informe seu nome';
        } else if (type === 'register' && values.name.trim().length > 100) {
            errors.name = 'O nome deve ter no máximo 100 caracteres';
        }

        setFieldErrors(errors);
        return Object.keys(errors).length === 0;
    }

    async function handleSubmit(event) {
        event.preventDefault();

        if (!validate()) return;

        const user = type === 'register'
            ? await register(values)
            : await login(values);

        if (user) {
            notifications.show({
                title: type === 'register' ? 'Conta criada!' : 'Bem-vindo de volta!',
                message: `Olá, ${user.name}.`,
                color: 'green',
            });
            navigate('/');
        }
    }

    function handleSocial() {
        notifications.show({
            title: 'Em breve',
            message: 'Login social ainda não está disponível.',
            color: 'blue',
        });
    }

    return (
        <div className={classes.wrapper}>
            <Paper className={classes.card} radius="md" p="xl" withBorder>
                <div className={classes.brand}>
                    <img src={logo} alt="Studex" className={classes.logo} />
                    <Title order={3}>Studex</Title>
                </div>

                <Text size="lg" fw={500} ta="center">
                    Bem-vindo ao Studex, {type === 'register' ? 'cadastre-se' : 'entre'} com
                </Text>

                <Group grow mb="md" mt="md">
                    <Button variant="default" radius="xl" leftSection={<IconBrandGoogle size={16} />} onClick={handleSocial}>
                        Google
                    </Button>
                    <Button variant="default" radius="xl" leftSection={<IconBrandGithub size={16} />} onClick={handleSocial}>
                        GitHub
                    </Button>
                </Group>

                <Divider label="Ou continue com email" labelPosition="center" my="lg" />

                <form onSubmit={handleSubmit}>
                    <Stack>
                        {type === 'register' && (
                            <TextInput
                                label="Nome"
                                placeholder="Seu nome"
                                value={values.name}
                                onChange={(e) => setField('name', e.currentTarget.value)}
                                error={fieldErrors.name}
                                radius="md"
                            />
                        )}

                        <TextInput
                            required
                            label="Email"
                            placeholder="voce@email.com"
                            value={values.email}
                            onChange={(e) => setField('email', e.currentTarget.value)}
                            error={fieldErrors.email}
                            radius="md"
                        />

                        <PasswordInput
                            required
                            label="Senha"
                            placeholder="Sua senha"
                            value={values.password}
                            onChange={(e) => setField('password', e.currentTarget.value)}
                            error={fieldErrors.password}
                            radius="md"
                        />

                        {type === 'register' && (
                            <Checkbox
                                label="Aceito os termos e condições"
                                checked={values.terms}
                                onChange={(e) => setField('terms', e.currentTarget.checked)}
                            />
                        )}

                        {error && (
                            <Text c="red.6" size="sm">
                                {error}
                            </Text>
                        )}
                    </Stack>

                    <Group justify="space-between" mt="xl">
                        <Anchor component="button" type="button" c="dimmed" onClick={() => toggle()} size="xs">
                            {type === 'register'
                                ? 'Já tem uma conta? Entre'
                                : 'Não tem uma conta? Cadastre-se'}
                        </Anchor>
                        <Button type="submit" radius="xl" loading={loading}>
                            {upperFirst(type === 'register' ? 'cadastrar' : 'entrar')}
                        </Button>
                    </Group>
                </form>
            </Paper>
        </div>
    );
}
