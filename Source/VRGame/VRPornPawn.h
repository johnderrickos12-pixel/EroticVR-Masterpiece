// VRPornPawn.h

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "VRPornPawn.generated.h"

// Forward declarations to improve compile times
class USceneComponent;
class UCameraComponent;
class UMotionControllerComponent;
class UPhysicsHandleComponent;
class UPrimitiveComponent;

UCLASS()
class VRGAME_API AVRPornPawn : public APawn
{
	GENERATED_BODY()

public:
	// Sets default values for this pawn's properties
	AVRPornPawn();

protected:
	// Called when the game starts or when spawned
	virtual void BeginPlay() override;

public:	
	// Called every frame
	virtual void Tick(float DeltaTime) override;

	// Called to bind functionality to input
	virtual void SetupPlayerInputComponent(class UInputComponent* PlayerInputComponent) override;

private:
	// --- Components ---

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
	USceneComponent* VRTrackingCenter;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
	UCameraComponent* HeadCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
	UMotionControllerComponent* LeftController;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
	UMotionControllerComponent* RightController;
	
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
	UPhysicsHandleComponent* LeftPhysicsHandle;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
	UPhysicsHandleComponent* RightPhysicsHandle;

	// --- Grab Logic ---

	void GrabLeft();
	void ReleaseLeft();

	void GrabRight();
	void ReleaseRight();

	// --- Configuration ---
	UPROPERTY(EditDefaultsOnly, Category = "Grab")
	float GrabRadius = 10.0f; // Radius in cm to check for grabbable objects

	// --- Helper Functions ---
	UPrimitiveComponent* FindGrabbableComponent(UMotionControllerComponent* Controller);
};
