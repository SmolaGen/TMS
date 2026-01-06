import React, { useEffect, useRef } from 'react';
import { Timeline } from 'vis-timeline/standalone';
import { DataSet } from 'vis-data/standalone';
import { useOrders, useMoveOrder } from '../../hooks/useOrders';
import type { TimelineDriver } from '../../types/api';
import 'vis-timeline/styles/vis-timeline-graph2d.css';

// Локальные типы для vis-timeline
interface VisTimelineItem {
    id: string | number;
    group?: string | number;
    content: string;
    start: Date;
    end?: Date;
    className?: string;
    editable?: boolean;
}

interface VisTimelineGroup {
    id: string | number;
    content: string;
}

interface VisTimelineOptions {
    editable?: {
        add?: boolean;
        updateTime?: boolean;
        updateGroup?: boolean;
        remove?: boolean;
    };
    stack?: boolean;
    orientation?: string;
    margin?: {
        item?: number;
        axis?: number;
    };
    zoomable?: boolean;
    zoomKey?: string;
    horizontalScroll?: boolean;
    showCurrentTime?: boolean;
    snap?: (date: Date, scale: string, step: number) => Date;
    onMove?: (item: VisTimelineItem, callback: (item: VisTimelineItem | null) => void) => void;
    onMoving?: (item: VisTimelineItem, callback: (item: VisTimelineItem | null) => void) => void;
}

interface TimelineViewProps {
    dateRange?: [Date, Date];
    drivers: TimelineDriver[];
    orders?: Array<{
        id: string;
        group: string;
        content: string;
        start: Date;
        end: Date;
        className?: string;
    }>;
    onOrderSelect?: (orderId: number) => void;
    selectedOrderId?: number | string | null;
}

export const TimelineView: React.FC<TimelineViewProps> = ({
    dateRange,
    drivers,
    orders: externalOrders = [],
    onOrderSelect,
    selectedOrderId,
}) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const timelineRef = useRef<Timeline | null>(null);
    const itemsDataSet = useRef(new DataSet<VisTimelineItem>([]));
    const groupsDataSet = useRef(new DataSet<VisTimelineGroup>([]));

    const { data: orders = [] } = useOrders(dateRange);
    const { handleMove } = useMoveOrder();

    // Инициализация Timeline
    useEffect(() => {
        if (!containerRef.current) return;

        const options: VisTimelineOptions = {
            editable: {
                add: false,
                updateTime: true,
                updateGroup: true,
                remove: false,
            },
            stack: true,
            orientation: 'top',
            margin: {
                item: 10,
                axis: 5,
            },
            zoomable: true,
            zoomKey: 'ctrlKey',
            horizontalScroll: true,
            showCurrentTime: true,
            snap: (date: Date) => {
                // Snap к 15-минутным интервалам
                const minutes = date.getMinutes();
                const snapped = Math.round(minutes / 15) * 15;
                const newDate = new Date(date);
                newDate.setMinutes(snapped);
                newDate.setSeconds(0);
                newDate.setMilliseconds(0);
                return newDate;
            },

            // Callback при перемещении - Optimistic UI
            onMove: (item, callback) => {
                handleMove(item as any, callback as any);
            },

            // Валидация во время перемещения
            onMoving: (item, callback) => {
                callback(item);
            },
        };

        const timeline = new Timeline(
            containerRef.current,
            itemsDataSet.current,
            groupsDataSet.current,
            options as any
        );

        timeline.on('select', (properties: { items: (string | number)[] }) => {
            if (properties.items.length > 0 && onOrderSelect) {
                onOrderSelect(Number(properties.items[0]));
            }
        });

        timelineRef.current = timeline;

        // Cleanup при unmount
        return () => {
            timeline.destroy();
            timelineRef.current = null;
        };
    }, [handleMove, onOrderSelect]);

    // Синхронизация заказов с DataSet
    useEffect(() => {
        const allOrders = [
            ...orders.map(o => ({
                ...o,
                start: new Date(o.start),
                end: o.end ? new Date(o.end) : undefined,
            })),
            ...externalOrders,
        ];
        itemsDataSet.current.clear();
        itemsDataSet.current.add(allOrders as VisTimelineItem[]);
    }, [orders, externalOrders]);

    // Синхронизация водителей (групп) с DataSet
    useEffect(() => {
        groupsDataSet.current.clear();
        groupsDataSet.current.add(drivers as unknown as VisTimelineGroup[]);
    }, [drivers]);

    // Прокрутка к выбранному заказу
    useEffect(() => {
        if (selectedOrderId && timelineRef.current) {
            timelineRef.current.setSelection(String(selectedOrderId));
            timelineRef.current.focus(String(selectedOrderId), { animation: true });
        }
    }, [selectedOrderId]);

    return (
        <div
            ref={containerRef}
            style={{
                height: '100%',
                minHeight: 200,
                background: '#fff',
            }}
        />
    );
};

