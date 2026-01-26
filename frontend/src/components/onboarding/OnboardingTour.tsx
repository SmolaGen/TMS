import React, { useEffect, useState } from 'react';
import { Tour } from 'antd';
import { useOnboarding } from '../../hooks/useOnboarding';

interface TourStep {
    selector: string;
    title: string;
    description: React.ReactNode;
    placement?: 'top' | 'left' | 'right' | 'bottom' | 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight';
}

interface OnboardingTourProps {
    open: boolean;
    onClose?: () => void;
}

export const OnboardingTour: React.FC<OnboardingTourProps> = ({ open, onClose }) => {
    const {
        currentStep,
        isLoading,
        nextStep,
        skipOnboarding,
        completeOnboarding,
        goToStep,
    } = useOnboarding();

    const [current, setCurrent] = useState<number>(0);

    // Синхронизируем текущий шаг с шагом из хука при открытии
    useEffect(() => {
        if (open && currentStep !== null) {
            setCurrent(currentStep - 1); // Шаги в Tour начинаются с 0
        } else if (open && currentStep === null) {
            setCurrent(0); // Начинаем с первого шага
        }
    }, [open, currentStep]);

    const steps: TourStep[] = [
        {
            selector: '[data-tour="create-order-btn"]',
            title: 'Создание заказа',
            description: (
                <div>
                    <p>
                        Нажмите эту кнопку, чтобы создать новый заказ. Вы сможете указать точки
                        отправления и назначения, временной интервал и приоритет.
                    </p>
                    <p style={{ marginTop: 8, color: '#1890ff', fontWeight: 500 }}>
                        💡 Совет: Вы можете создать заказ без назначения водителя и сделать это позже.
                    </p>
                </div>
            ),
            placement: 'bottom',
        },
        {
            selector: '[data-tour="timeline"]',
            title: 'Временная шкала',
            description: (
                <div>
                    <p>
                        Здесь отображаются все заказы в виде временной шкалы. Каждый заказ показан
                        как полоска с временем выполнения.
                    </p>
                    <p style={{ marginTop: 8 }}>
                        Кликните на заказ для выбора, затем перетащите его на другого водителя
                        или измените время, перетащив полоску.
                    </p>
                </div>
            ),
            placement: 'right',
        },
        {
            selector: '[data-tour="map-tab"]',
            title: 'Карта водителей',
            description: (
                <div>
                    <p>
                        Переключитесь на вкладку карты, чтобы видеть локации всех водителей
                        в реальном времени.
                    </p>
                    <p style={{ marginTop: 8 }}>
                        <span style={{ color: '#52c41a', fontWeight: 500 }}>Зелёный</span> — доступен,{' '}
                        <span style={{ color: '#faad14', fontWeight: 500 }}>жёлтый</span> — занят.
                    </p>
                    <p style={{ marginTop: 8, color: '#1890ff', fontWeight: 500 }}>
                        💡 Совет: Локации обновляются автоматически каждые 30 секунд.
                    </p>
                </div>
            ),
            placement: 'bottom',
        },
        {
            selector: '[data-tour="status-select"]',
            title: 'Изменение статуса',
            description: (
                <div>
                    <p>
                        Изменяйте статусы заказов для отслеживания прогресса выполнения.
                        Доступные статусы:
                    </p>
                    <ul style={{ paddingLeft: 20, marginTop: 8 }}>
                        <li><strong>Pending</strong> — ожидает назначения водителя</li>
                        <li><strong>Assigned</strong> — водитель назначен</li>
                        <li><strong>In Progress</strong> — заказ в выполнении</li>
                        <li><strong>Completed</strong> — заказ завершён</li>
                    </ul>
                    <p style={{ marginTop: 8, color: '#1890ff', fontWeight: 500 }}>
                        💡 Совет: История изменений статусов сохраняется в деталях заказа.
                    </p>
                </div>
            ),
            placement: 'bottom',
        },
        {
            selector: '[data-tour="driver-list"]',
            title: 'Статистика водителя',
            description: (
                <div>
                    <p>
                        Кликните на водителя в списке или Timeline, чтобы увидеть детальную
                        статистику за период:
                    </p>
                    <ul style={{ paddingLeft: 20, marginTop: 8 }}>
                        <li>Количество выполненных заказов</li>
                        <li>Процент завершения (completion rate)</li>
                        <li>Общий доход и пройденное расстояние</li>
                    </ul>
                    <p style={{ marginTop: 8, color: '#1890ff', fontWeight: 500 }}>
                        💡 Совет: Статистика обновляется раз в сутки для предыдущего дня.
                    </p>
                </div>
            ),
            placement: 'left',
        },
    ];

    const handleClose = async () => {
        if (onClose) {
            onClose();
        }
    };

    const handleCurrentChange = async (currentStep: number) => {
        setCurrent(currentStep);
        // Обновляем шаг на сервере (шаги API начинаются с 1)
        await goToStep(currentStep + 1);
    };

    const handleFinish = async () => {
        await completeOnboarding();
        handleClose();
    };

    const handleCloseTour = async () => {
        await skipOnboarding();
        handleClose();
    };

    return (
        <Tour
            open={open}
            onClose={handleCloseTour}
            current={current}
            onChange={handleCurrentChange}
            onFinish={handleFinish}
            steps={steps}
            loading={isLoading}
            indicatorsRender={(total, current) => {
                return (
                    <span>
                        {current + 1} / {total}
                    </span>
                );
            }}
        />
    );
};
