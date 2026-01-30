from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.schemas.template import (
    OrderTemplateCreate,
    OrderTemplateUpdate,
    OrderTemplateResponse,
    GenerateOrdersRequest
)
from src.schemas.order import OrderResponse
from src.services.template_service import TemplateService
from src.api.dependencies import get_template_service

router = APIRouter()


@router.get("/templates", response_model=List[OrderTemplateResponse])
async def list_templates(
    contractor_id: Optional[int] = Query(None, description="Фильтр по ID подрядчика"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности шаблона"),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Получить список всех шаблонов заказов с опциональными фильтрами.
    """
    templates = await template_service.list_templates(
        contractor_id=contractor_id,
        is_active=is_active
    )
    return templates


@router.post("/templates", response_model=OrderTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: OrderTemplateCreate,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Создать новый шаблон заказа.
    """
    try:
        template = await template_service.create_template(data)
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/templates/{template_id}", response_model=OrderTemplateResponse)
async def get_template(
    template_id: int,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Получить шаблон заказа по ID.
    """
    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Шаблон с ID {template_id} не найден"
        )
    return template


@router.patch("/templates/{template_id}", response_model=OrderTemplateResponse)
async def update_template(
    template_id: int,
    data: OrderTemplateUpdate,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Обновить существующий шаблон заказа.
    """
    try:
        template = await template_service.update_template(template_id, data)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Шаблон с ID {template_id} не найден"
            )
        return template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Удалить шаблон заказа.
    """
    success = await template_service.delete_template(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Шаблон с ID {template_id} не найден"
        )


@router.post("/templates/{template_id}/generate", response_model=List[OrderResponse])
async def generate_orders_from_template(
    template_id: int,
    request: GenerateOrdersRequest,
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Сгенерировать заказы из шаблона для заданного периода.

    Создает заказы по одному на каждый день в указанном диапазоне дат.
    """
    try:
        orders = await template_service.generate_orders_from_template(
            template_id=template_id,
            request=request
        )
        return orders
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
