import { useEffect, useCallback, useRef } from 'react';

type KeyboardHandler = () => void;

interface ShortcutConfig {
    key: string;
    ctrlKey?: boolean;
    altKey?: boolean;
    shiftKey?: boolean;
    handler: KeyboardHandler;
    description: string;
}

interface UseKeyboardShortcutsOptions {
    enabled?: boolean;
    preventDefault?: boolean;
}

/**
 * Хук для управления горячими клавишами
 * 
 * @example
 * useKeyboardShortcuts([
 *   { key: 'n', handler: openNewOrder, description: 'Новый заказ' },
 *   { key: 'f', handler: focusSearch, description: 'Фокус на поиск' },
 *   { key: 'Escape', handler: closeModal, description: 'Закрыть' },
 * ]);
 */
export const useKeyboardShortcuts = (
    shortcuts: ShortcutConfig[],
    options: UseKeyboardShortcutsOptions = {}
) => {
    const { enabled = true, preventDefault = true } = options;
    const shortcutsRef = useRef(shortcuts);
    shortcutsRef.current = shortcuts;

    const handleKeyDown = useCallback((event: KeyboardEvent) => {
        // Игнорируем, если фокус в input/textarea
        const target = event.target as HTMLElement;
        if (
            target.tagName === 'INPUT' ||
            target.tagName === 'TEXTAREA' ||
            target.isContentEditable
        ) {
            // Разрешаем только Escape в полях ввода
            if (event.key !== 'Escape') return;
        }

        const eventKey = event.key.toLowerCase();

        for (const shortcut of shortcutsRef.current) {
            const shortcutKey = shortcut.key.toLowerCase();

            const keyMatch = eventKey === shortcutKey;
            const ctrlMatch = !!shortcut.ctrlKey === (event.ctrlKey || event.metaKey);
            const altMatch = !!shortcut.altKey === event.altKey;
            const shiftMatch = !!shortcut.shiftKey === event.shiftKey;

            if (keyMatch && ctrlMatch && altMatch && shiftMatch) {
                if (preventDefault) {
                    event.preventDefault();
                }
                shortcut.handler();
                return;
            }
        }
    }, [preventDefault]);

    useEffect(() => {
        if (!enabled) return;

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [enabled, handleKeyDown]);

    // Возвращаем список шорткатов для отображения в UI (например, в Tooltip)
    return {
        shortcuts: shortcuts.map(s => ({
            key: s.key,
            modifiers: [
                s.ctrlKey && '⌘',
                s.altKey && '⌥',
                s.shiftKey && '⇧',
            ].filter(Boolean).join(''),
            description: s.description,
        })),
    };
};
