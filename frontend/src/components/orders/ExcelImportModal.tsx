import React, { useState } from 'react';
import { Modal, Upload, Button, List, Typography, Space } from 'antd';
import { InboxOutlined, FileExcelOutlined } from '@ant-design/icons';
import { useImportOrders } from '../../hooks/useOrders';

const { Dragger } = Upload;
const { Text } = Typography;

interface ExcelImportModalProps {
  open: boolean;
  onCancel: () => void;
}

export const ExcelImportModal: React.FC<ExcelImportModalProps> = ({ open, onCancel }) => {
  const [fileList, setFileList] = useState<any[]>([]);
  const { mutate: importOrders, isPending } = useImportOrders();

  const handleImport = () => {
    if (fileList.length === 0) return;

    const file = fileList[0].originFileObj;
    importOrders(file, {
      onSuccess: () => {
        setFileList([]);
        onCancel();
      },
    });
  };

  const uploadProps = {
    onRemove: (_file: any) => {
      setFileList([]);
    },
    beforeUpload: (file: any) => {
      setFileList([file]);
      return false; // Prevent automatic upload
    },
    fileList,
    accept: '.xlsx, .xls',
    maxCount: 1,
  };

  return (
    <Modal
      title="Импорт заказов из Excel"
      open={open}
      onCancel={onCancel}
      footer={[
        <Button key="back" onClick={onCancel}>
          Отмена
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={isPending}
          onClick={handleImport}
          disabled={fileList.length === 0}
        >
          Загрузить и импортировать
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Text type="secondary">
          Выберите Excel файл со списком заказов. Ожидаемые колонки:
          <b> Адрес погрузки, Адрес выгрузки, Дата, Время, Приоритет, Телефон, Имя, Комментарий</b>.
        </Text>

        <Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Нажмите или перетащите файл в эту область</p>
          <p className="ant-upload-hint">Поддерживаются файлы .xlsx и .xls</p>
        </Dragger>

        {fileList.length > 0 && (
          <List
            size="small"
            bordered
            dataSource={fileList}
            renderItem={(file) => (
              <List.Item>
                <Space>
                  <FileExcelOutlined style={{ color: '#1d6f42' }} />
                  {file.name}
                </Space>
              </List.Item>
            )}
          />
        )}
      </Space>
    </Modal>
  );
};
