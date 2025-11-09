from fastapi-app.app.models.orm.base import Base, UUIDMixin, AuditMixin

print("UUIDMixin attributes:")
for attr in dir(UUIDMixin):
    if not attr.startswith('_'):
        print(f"  {attr}: {getattr(UUIDMixin, attr)}")

print("\nBase attributes:")
for attr in dir(Base):
    if not attr.startswith('_'):
        print(f"  {attr}: {getattr(Base, attr)}")
