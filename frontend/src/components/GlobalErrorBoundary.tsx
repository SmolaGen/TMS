import React, { type ErrorInfo } from 'react';
import { Result, Button, Typography } from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface Props {
    children: React.ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class GlobalErrorBoundary extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null
        };
    }

    static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Global Error Boundary caught an error:', error, errorInfo);
    }

    handleReload = () => {
        window.location.reload();
    };

    handleGoHome = () => {
        window.location.href = '/';
    };

    render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    height: '100vh',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'var(--tms-bg-layout)',
                    padding: '20px'
                }}>
                    <Result
                        status="error"
                        title="Что-то пошло не так"
                        subTitle={
                            <div style={{ textAlign: 'center' }}>
                                <Text type="secondary">
                                    Произошла непредвиденная ошибка. Мы уже работаем над её исправлением.
                                </Text>
                                {this.state.error && (
                                    <div style={{ marginTop: '16px' }}>
                                        <Text type="danger" code>
                                            {this.state.error.message}
                                        </Text>
                                    </div>
                                )}
                            </div>
                        }
                        extra={[
                            <Button
                                type="primary"
                                key="reload"
                                icon={<ReloadOutlined />}
                                onClick={this.handleReload}
                            >
                                Обновить страницу
                            </Button>,
                            <Button
                                key="home"
                                icon={<HomeOutlined />}
                                onClick={this.handleGoHome}
                            >
                                На главную
                            </Button>,
                        ]}
                    />
                </div>
            );
        }

        return this.props.children;
    }
}
