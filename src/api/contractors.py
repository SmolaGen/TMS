from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.connection import async_session_factory
from src.database.models import Contractor, Order, OrderStatus
from src.schemas.contractor import ContractorOrdersRequest, ContractorBatchResponse, ContractorOrderResponse
from src.services.order_service import OrderService
from src.api.dependencies import get_order_service
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/contractors", tags=["Contractors"])

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_db():
    async with async_session_factory() as session:
        yield session

async def get_contractor(
    api_key: str = Security(api_key_header),
    session: AsyncSession = Depends(get_db)
) -> Contractor:
    """Проверка API ключа подрядчика."""
    query = select(Contractor).where(Contractor.api_key == api_key, Contractor.is_active == True)
    result = await session.execute(query)
    contractor = result.scalar_one_or_none()
    
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API Key"
        )
    return contractor

@router.post("/orders", response_model=ContractorBatchResponse)
async def create_orders_batch(
    request: ContractorOrdersRequest,
    contractor: Contractor = Depends(get_contractor),
    order_service: OrderService = Depends(get_order_service)
):
    """Пакетное создание заказов от подрядчика."""
    logger.info("contractor_batch_import", contractor_id=contractor.id, count=len(request.orders))
    
    created_count = 0
    errors = []
    
    for order_dto in request.orders:
        try:
            # Преобразуем ContractorOrderCreate в OrderCreate если нужно, 
            # или расширим OrderService для работы с доп. полями.
            # Для простоты используем текущий OrderService.create_order
            # Но нам нужно сохранить external_id и contractor_id.
            
            # TODO: В идеале OrderService должен уметь принимать эти поля
            # Пока сделаем напрямую через сессию или расширим OrderService
            
            # Поскольку OrderService.create_order делает commit внутри UoW, 
            # нам нужно будет обновить заказ после создания или изменить OrderService
            
            from src.schemas.order import OrderCreate
            base_order_dto = OrderCreate(
                contractor_id=contractor.id,
                external_id=order_dto.external_id,
                pickup_address=order_dto.pickup_address,
                pickup_lat=order_dto.pickup_lat,
                pickup_lon=order_dto.pickup_lon,
                dropoff_address=order_dto.dropoff_address,
                dropoff_lat=order_dto.dropoff_lat,
                dropoff_lon=order_dto.dropoff_lon,
                time_start=order_dto.time_start,
                priority=order_dto.priority,
                customer_phone=order_dto.customer_phone,
                customer_name=order_dto.customer_name,
                comment=order_dto.comment
            )
            
            await order_service.create_order(base_order_dto)
            created_count += 1
            
        except HTTPException as e:
            errors.append({"external_id": order_dto.external_id, "error": e.detail})
        except Exception as e:
            logger.exception("contractor_order_failed", external_id=order_dto.external_id)
            errors.append({"external_id": order_dto.external_id, "error": str(e)})
            
    return ContractorBatchResponse(
        processed=len(request.orders),
        created=created_count,
        errors=errors
    )

@router.get("/orders/{external_id}", response_model=ContractorOrderResponse)
async def get_order_status(
    external_id: str,
    contractor: Contractor = Depends(get_contractor),
    session: AsyncSession = Depends(get_db)
):
    """Получение статуса заказа по внешнему ID."""
    query = select(Order).where(
        Order.external_id == external_id,
        Order.contractor_id == contractor.id
    )
    result = await session.execute(query)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return order

@router.post("/webhook")
async def register_webhook(
    url: str,
    contractor: Contractor = Depends(get_contractor),
    session: AsyncSession = Depends(get_db)
):
    """Регистрация/обновление URL вебхука для подрядчика."""
    contractor.webhook_url = url
    await session.commit()
    logger.info("contractor_webhook_updated", contractor_id=contractor.id, url=url)
    return {"status": "success", "webhook_url": url}
