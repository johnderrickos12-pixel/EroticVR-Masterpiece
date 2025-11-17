// VRPornPawn.cpp

#include "VRPornPawn.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "MotionControllerComponent.h"
#include "PhysicsEngine/PhysicsHandleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "DrawDebugHelpers.h"

// Sets default values
AVRPornPawn::AVRPornPawn()
{
 	// Set this pawn to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = true;

	// Create the core components
	VRTrackingCenter = CreateDefaultSubobject<USceneComponent>(TEXT("VRTrackingCenter"));
	SetRootComponent(VRTrackingCenter);

	HeadCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("HeadCamera"));
	HeadCamera->SetupAttachment(VRTrackingCenter);

	LeftController = CreateDefaultSubobject<UMotionControllerComponent>(TEXT("LeftController"));
	LeftController->SetupAttachment(VRTrackingCenter);
	LeftController->SetTrackingSource(EControllerHand::Left);

	RightController = CreateDefaultSubobject<UMotionControllerComponent>(TEXT("RightController"));
	RightController->SetupAttachment(VRTrackingCenter);
	RightController->SetTrackingSource(EControllerHand::Right);
	
	LeftPhysicsHandle = CreateDefaultSubobject<UPhysicsHandleComponent>(TEXT("LeftPhysicsHandle"));
	RightPhysicsHandle = CreateDefaultSubobject<UPhysicsHandleComponent>(TEXT("RightPhysicsHandle"));
}

// Called when the game starts or when spawned
void AVRPornPawn::BeginPlay()
{
	Super::BeginPlay();
}

// Called every frame
void AVRPornPawn::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// If we are holding an object, update the physics handle's target location every frame
	if (LeftPhysicsHandle->GetGrabbedComponent())
	{
		LeftPhysicsHandle->SetTargetLocation(LeftController->GetComponentLocation());
	}
	if (RightPhysicsHandle->GetGrabbedComponent())
	{
		RightPhysicsHandle->SetTargetLocation(RightController->GetComponentLocation());
	}
}

// Called to bind functionality to input
void AVRPornPawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	// Bind grab actions
	PlayerInputComponent->BindAction("GrabLeft", IE_Pressed, this, &AVRPornPawn::GrabLeft);
	PlayerInputComponent->BindAction("GrabLeft", IE_Released, this, &AVRPornPawn::ReleaseLeft);

	PlayerInputComponent->BindAction("GrabRight", IE_Pressed, this, &AVRPornPawn::GrabRight);
	PlayerInputComponent->BindAction("GrabRight", IE_Released, this, &AVRPornPawn::ReleaseRight);
}

void AVRPornPawn::GrabLeft()
{
	UPrimitiveComponent* ComponentToGrab = FindGrabbableComponent(LeftController);
	if (ComponentToGrab)
	{
		LeftPhysicsHandle->GrabComponentAtLocationWithRotation(
			ComponentToGrab,
			NAME_None, // Optional bone name
			ComponentToGrab->GetCenterOfMass(),
			ComponentToGrab->GetComponentRotation()
		);
	}
}

void AVRPornPawn::ReleaseLeft()
{
	if (LeftPhysicsHandle->GetGrabbedComponent())
	{
		LeftPhysicsHandle->ReleaseComponent();
	}
}

void AVRPornPawn::GrabRight()
{
	UPrimitiveComponent* ComponentToGrab = FindGrabbableComponent(RightController);
	if (ComponentToGrab)
	{
		RightPhysicsHandle->GrabComponentAtLocationWithRotation(
			ComponentToGrab,
			NAME_None, // Optional bone name
			ComponentToGrab->GetCenterOfMass(),
			ComponentToGrab->GetComponentRotation()
		);
	}
}

void AVRPornPawn::ReleaseRight()
{
	if (RightPhysicsHandle->GetGrabbedComponent())
	{
		RightPhysicsHandle->ReleaseComponent();
	}
}

UPrimitiveComponent* AVRPornPawn::FindGrabbableComponent(UMotionControllerComponent* Controller)
{
	FVector Start = Controller->GetComponentLocation();
	TArray<FOverlapResult> OverlapResults;
	FCollisionShape Sphere = FCollisionShape::MakeSphere(GrabRadius);

	bool bHasHit = GetWorld()->OverlapMultiByObjectType(
		OverlapResults,
		Start,
		FQuat::Identity,
		FCollisionObjectQueryParams(ECollisionChannel::ECC_PhysicsBody),
		Sphere
	);

	// For debugging, draw the sphere
	// DrawDebugSphere(GetWorld(), Start, GrabRadius, 12, FColor::Red, false, 2.0f);

	if (bHasHit)
	{
		for (FOverlapResult Result : OverlapResults)
		{
			UPrimitiveComponent* PrimitiveComponent = Result.GetComponent();
			if (PrimitiveComponent && PrimitiveComponent->IsSimulatingPhysics())
			{
				return PrimitiveComponent; // Return the first physics-enabled component we find
			}
		}
	}
	
	return nullptr;
}
