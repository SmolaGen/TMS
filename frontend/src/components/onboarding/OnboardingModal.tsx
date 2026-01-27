import React, { useEffect, useState, useMemo } from 'react';
import { Modal, Steps, Button, Space, Typography, Popconfirm } from 'antd';
import { ArrowLeftOutlined, ArrowRightOutlined, CloseOutlined } from '@ant-design/icons';
import { useOnboarding } from '../../hooks/useOnboarding';
import { useTelegramAuth } from '../../hooks/useTelegramAuth';


const { Title, Paragraph, Text } = Typography;

interface OnboardingModalProps {
    open: boolean;
    onClose: () => void;
}

interface StepContent {
    title: string;
    description: string;
    content: React.ReactNode;
}

export const OnboardingModal: React.FC<OnboardingModalProps> = ({ open, onClose }) => {
    const {
        currentStep,
        isLoading,
        skipOnboarding,
        completeOnboarding,
        goToStep,
    } = useOnboarding();

    const { user } = useTelegramAuth();
    const userRole = user?.role;

    const [internalStep, setInternalStep] = useState<number>(0);

    // Синхронизируем внутренний шаг с шагом из хука при открытии
    useEffect(() => {
        if (open && currentStep !== null) {
            setInternalStep(currentStep - 1); // Шаги в UI начинаются с 0
        } else if (open && currentStep === null) {
            setInternalStep(0); // Начинаем с первого шага
        }
    }, [open, currentStep]);

    // Адаптивный контент онбординга в зависимости от роли пользователя
    const stepsData: StepContent[] = useMemo(() => {
        // Шаги для администраторов - фокус на управлении и аналитике
        if (userRole === 'admin') {
            return [
                {
                    title: 'Обзор системы',
                    description: 'Дашборд и ключевые метрики',
                    content: (
                        <div>
                            <Title level={4}>Обзор системы</Title>
                            <Paragraph>
                                Добро пожаловать! Как администратор, вы видите полную картину работы диспетчерской службы.
                            </Paragraph>
                            <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                                <li><Text strong>Дашборд</Text> — ключевая информация на одном экране</li>
                                <li>Активные заказы и их статусы</li>
                                <li>Количество доступных водителей</li>
                                <li>Показатели эффективности за день</li>
                            </ul>
                            <Paragraph type="secondary">
                                💡 Совет: Используйте дашборд для быстрого мониторинга текущей ситуации.
                            </Paragraph>
                        </div>
                    ),
                },
                {
                    title: 'Управление заказами',
                    description: 'Контроль и распределение заказов',
                    content: (
                        <div>
                            <Title level={4}>Управление заказами</Title>
                            <Paragraph>
                                Вы можете создавать, распределять и контролировать выполнение всех заказов в системе.
                            </Paragraph>
                            <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                                <li>Создавайте заказы через кнопку <Text strong>"Создать заказ"</Text></li>
                                <li>Назначайте водителей автоматически или вручную</li>
                                <li>Отслеживайте статусы в реальном времени</li>
                                <li>Вовремя реагируйте на проблемы</li>
                            </ul>
                            <Paragraph type="secondary">
                                💡 Совет: Используйте Timeline для визуального распределения заказов по времени.
                            </Paragraph>
                        </div>
                    ),
                },
                {
                    title: 'Мониторинг водителей',
                    description: 'Карта и статусы в реальном времени',
                    content: (
                        <div>
                            <Title level={4}>Мониторинг водителей</Title>
                            <Paragraph>
                                Отслеживайте расположение и статус всех водителей на карте в реальном времени.
                            </Paragraph>
                            <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                                <li>Перейдите на вкладку <Text strong>"Карта"</Text></li>
                                <li>Видите всех водителей с их статусами</li>
                                <li><Text type="success">Зелёный</Text> — доступен, <Text type="warning">Жёлтый</Text> — в пути</li>
                                <li>Кликните на водителя для детальной информации</li>
                            </ul>
                            <Paragraph type="secondary">
                                💡 Совет: Локации обновляются автоматически каждые 30 секунд.
                            </Paragraph>
                        </div>
                    ),
                },
                {
                    title: 'Статистика и аналитика',
                    description: 'Анализ эффективности работы',
                    content: (
                        <div>
                            <Title level={4}>Статистика и аналитика</Title>
                            <Paragraph>
                                Анализируйте показатели эффективности для принятия управленческих решений.
                            </Paragraph>
                            <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                                <li>Кликните на водителя в списке или Timeline</li>
                                <li>Откроется панель со статистикой за период</li>
                                <li>Количество выполненных заказов и отмен</li>
                                <li>Completion rate (процент завершения)</li>
                                <li>Общий доход и пройденное расстояние</li>
                            </ul>
                            <Paragraph type="secondary">
                                💡 Совет: Сравнивайте показатели водителей для выявления лучших сотрудников.
                            </Paragraph>
                        </div>
                    ),
                },
                {
                    title: 'Настройки системы',
                    description: 'Управление пользователями и настройками',
                    content: (
                        <div>
                            <Title level={4}>Настройки системы</Title>
                            <Paragraph>
                                Управляйте настройками системы и правами доступа.
                            </Paragraph>
                            <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                                <li>Перейдите в раздел <Text strong>"Настройки"</Text></li>
                                <li>Управляйте учётными записями водителей</li>
                                <li>Настраивайте параметры системы</li>
                                <li>Просматривайте логи действий</li>
                            </ul>
                            <Paragraph type="secondary">
                                💡 Совет: Вы можете в любой момент пройти онбординг заново из настроек.
                            </Paragraph>
                        </div>
                    ),
                },
            ];
        }

        // Шаги для диспетчеров - фокус на операционной работе
        return [
            {
                title: 'Создание заказа',
                description: 'Научитесь создавать новые заказы',
                content: (
                    <div>
                        <Title level={4}>Создание заказа</Title>
                        <Paragraph>
                            Заказы — основа вашей работы. Создавайте заказы для клиентов,
                            указывая точки отправления и назначения, временной интервал и приоритет.
                        </Paragraph>
                        <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                            <li>Нажмите кнопку <Text strong>"Создать заказ"</Text> в главном меню</li>
                            <li>Укажите адреса pickup и dropoff</li>
                            <li>Выберите временной интервал</li>
                            <li>Назначьте приоритет (нормальный по умолчанию)</li>
                            <li>Добавьте информацию о клиенте (опционально)</li>
                        </ul>
                        <Paragraph type="secondary">
                            💡 Совет: Вы можете создать заказ без назначения водителя и сделать это позже.
                        </Paragraph>
                    </div>
                ),
            },
            {
                title: 'Назначение водителя',
                description: 'Назначайте водителей на заказы',
                content: (
                    <div>
                        <Title level={4}>Назначение водителя</Title>
                        <Paragraph>
                            После создания заказа вы можете назначить водителя или изменить назначение.
                        </Paragraph>
                        <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                            <li>В Timeline кликните на заказ для его выбора</li>
                            <li>Перетащите заказ на другого водителя</li>
                            <li>Или используйте меню заказа для выбора водителя</li>
                        </ul>
                        <Paragraph type="secondary">
                            💡 Совет: Водители видят только свои назначенные заказы в мобильном приложении.
                        </Paragraph>
                    </div>
                ),
            },
            {
                title: 'Просмотр на карте',
                description: 'Отслеживайте водителей в реальном времени',
                content: (
                    <div>
                        <Title level={4}>Просмотр на карте</Title>
                        <Paragraph>
                            Карта показывает локации всех водителей в реальном времени.
                        </Paragraph>
                        <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                            <li>Перейдите на вкладку <Text strong>"Карта"</Text></li>
                            <li>Видите всех водителей с их статусами</li>
                            <li><Text type="success">Зелёный</Text> — доступен, <Text type="warning">Жёлтый</Text> — занят</li>
                            <li>Кликните на маркера водителя для деталей</li>
                        </ul>
                        <Paragraph type="secondary">
                            💡 Совет: Локации обновляются автоматически каждые 30 секунд.
                        </Paragraph>
                    </div>
                ),
            },
            {
                title: 'Изменение статуса',
                description: 'Управляйте статусами заказов',
                content: (
                    <div>
                        <Title level={4}>Изменение статуса заказа</Title>
                        <Paragraph>
                            Статусы заказов помогают отслеживать прогресс выполнения.
                        </Paragraph>
                        <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                            <li><Text strong>Pending</Text> — ожидает назначения водителя</li>
                            <li><Text strong>Assigned</Text> — водитель назначен</li>
                            <li><Text strong>In Progress</Text> — заказ в выполнении</li>
                            <li><Text strong>Completed</Text> — заказ завершён</li>
                        </ul>
                        <Paragraph>
                            Водители могут менять статусы через мобильное приложение,
                            а вы можете изменить их вручную из интерфейса диспетчера.
                        </Paragraph>
                        <Paragraph type="secondary">
                            💡 Совет: История изменений статусов сохраняется в деталях заказа.
                        </Paragraph>
                    </div>
                ),
            },
            {
                title: 'Просмотр статистики',
                description: 'Анализируйте эффективность работы',
                content: (
                    <div>
                        <Title level={4}>Просмотр статистики</Title>
                        <Paragraph>
                            Статистика помогает анализировать эффективность водителей и общую производительность.
                        </Paragraph>
                        <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
                            <li>Кликните на водителя в списке или Timeline</li>
                            <li>Откроется панель со статистикой за период</li>
                            <li>Видите количество выполненных заказов</li>
                            <li>Процент завершения (completion rate)</li>
                            <li>Общий доход и пройденное расстояние</li>
                        </ul>
                        <Paragraph type="secondary">
                            💡 Совет: Статистика обновляется раз в сутки для предыдущего дня.
                        </Paragraph>
                    </div>
                ),
            },
        ];
    }, [userRole]);

    const handleNext = async () => {
        if (internalStep < stepsData.length - 1) {
            const nextStepValue = internalStep + 2; // API шаги начинаются с 1
            await goToStep(nextStepValue);
            setInternalStep(internalStep + 1);
        } else {
            // Завершаем онбординг после последнего шага
            await completeOnboarding();
            handleClose();
        }
    };

    const handlePrevious = async () => {
        if (internalStep > 0) {
            const prevStepValue = internalStep; // API шаги начинаются с 1
            await goToStep(prevStepValue);
            setInternalStep(internalStep - 1);
        }
    };

    const handleSkip = async () => {
        await skipOnboarding();
        handleClose();
    };

    const handleClose = () => {
        setInternalStep(0);
        onClose();
    };

    const isLastStep = internalStep === stepsData.length - 1;
    const isFirstStep = internalStep === 0;

    // Адаптивный заголовок в зависимости от роли
    const modalTitle = useMemo(() => {
        if (userRole === 'admin') {
            return 'Добро пожаловать! Панель администратора';
        }
        return 'Добро пожаловать в систему диспетчеризации!';
    }, [userRole]);

    return (
        <Modal
            title={modalTitle}
            open={open}
            onCancel={handleClose}
            footer={null}
            width={700}
            destroyOnClose
            closeIcon={<CloseOutlined />}
        >
            <div style={{ padding: '20px 0' }}>
                <Steps
                    current={internalStep}
                    size="small"
                    style={{ marginBottom: 30 }}
                    items={stepsData.map((step) => ({
                        title: step.title,
                        description: step.description,
                    }))}
                />

                <div style={{
                    minHeight: 300,
                    padding: '20px',
                    backgroundColor: '#fafafa',
                    borderRadius: '8px',
                    border: '1px solid #f0f0f0'
                }}>
                    {stepsData[internalStep]?.content}
                </div>

                <div style={{
                    marginTop: 30,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <Space>
                        {!isFirstStep && (
                            <Button
                                icon={<ArrowLeftOutlined />}
                                onClick={handlePrevious}
                                disabled={isLoading}
                            >
                                Назад
                            </Button>
                        )}
                    </Space>

                    <Space>
                        <Popconfirm
                            title="Пропустить онбординг?"
                            description="Вы можете запустить его позже из настроек"
                            onConfirm={handleSkip}
                            okText="Да, пропустить"
                            cancelText="Отмена"
                        >
                            <Button type="link" disabled={isLoading}>
                                Пропустить
                            </Button>
                        </Popconfirm>

                        <Button
                            type="primary"
                            icon={isLastStep ? null : <ArrowRightOutlined />}
                            onClick={handleNext}
                            loading={isLoading}
                        >
                            {isLastStep ? 'Завершить' : 'Далее'}
                        </Button>
                    </Space>
                </div>

                <div style={{ textAlign: 'center', marginTop: 20 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        Шаг {internalStep + 1} из {stepsData.length}
                    </Text>
                </div>
            </div>
        </Modal>
    );
};
