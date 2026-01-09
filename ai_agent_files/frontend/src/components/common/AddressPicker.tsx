import React, { useState, useMemo } from 'react';
import { AutoComplete, Input, Spin } from 'antd';
import { useGeocoding } from '../../hooks/useGeocoding';
import { useDebounce } from '../../hooks/useDebounce';

interface AddressPickerProps {
    value?: string;
    onChange?: (address: string, lat: number, lon: number) => void;
    placeholder?: string;
}

export const AddressPicker: React.FC<AddressPickerProps> = ({ value, onChange, placeholder }) => {
    const [searchText, setSearchText] = useState(value || '');
    const debouncedSearch = useDebounce(searchText, 500);

    const { data: results = [], isLoading } = useGeocoding(debouncedSearch);

    const options = useMemo(() => {
        return results.map((r) => ({
            label: (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 500 }}>{r.name}</span>
                    <span style={{ fontSize: '12px', color: '#8c8c8c' }}>{r.address_full}</span>
                </div>
            ),
            value: r.address_full || r.name,
            ...r
        }));
    }, [results]);

    const handleSelect = (val: string, option: any) => {
        setSearchText(val);
        if (onChange) {
            onChange(val, option.lat, option.lon);
        }
    };

    return (
        <AutoComplete
            value={searchText}
            options={options}
            onSelect={handleSelect}
            onSearch={setSearchText}
            style={{ width: '100%' }}
        >
            <Input
                placeholder={placeholder}
                suffix={isLoading ? <Spin size="small" /> : null}
            />
        </AutoComplete>
    );
};
