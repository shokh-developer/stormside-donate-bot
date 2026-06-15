from handlers.start import router as start_router
from handlers.shop import router as shop_router
from handlers.payment import router as payment_router
from handlers.admin import router as admin_router
from handlers.support import router as support_router

all_routers = [start_router, shop_router, payment_router, admin_router, support_router]
