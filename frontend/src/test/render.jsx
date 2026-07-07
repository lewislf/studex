import { render as testingLibraryRender } from '@testing-library/react';
import { MantineProvider } from '@mantine/core';
import { theme } from '../styles/Mantine/theme';
import userEvent from '@testing-library/user-event';

export function render(ui) {
    return testingLibraryRender(<>{ui}</>, {
        wrapper: ({ children }) => (
            <MantineProvider theme={theme}>{children}</MantineProvider>
        ),
    });
}

export { userEvent };
export * from '@testing-library/react';
