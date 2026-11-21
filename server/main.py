from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import init_db
from routers import analytics, auth, budgets, cards, recurring, transactions, users
from services import AuthenticationError, BusinessRuleError, NotFoundError


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Budget Tracker API", lifespan=lifespan)

# Allow the client (dev server) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(AuthenticationError)
async def authentication_handler(_request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(NotFoundError)
async def not_found_handler(_request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(_request: Request, exc: BusinessRuleError):
    return JSONResponse(status_code=422, content={"detail": exc.message})


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(budgets.router)
app.include_router(cards.router)
app.include_router(transactions.router)
app.include_router(recurring.router)
app.include_router(analytics.router)


@app.get("/")
def read_root():
    return {"message": "Budget Tracker API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
