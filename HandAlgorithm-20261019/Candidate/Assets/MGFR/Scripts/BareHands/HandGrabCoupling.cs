using UnityEngine;

namespace MGFR.BareHands
{
 public sealed class HandGrabCoupling:MonoBehaviour
 {
  public Rigidbody Body;
  public Vector3 LocalAnchor,PreviousTarget,TargetOffset;
  public Collider Surface;
  float age;
  public Vector3 Target(Vector3 pinch)=>pinch+TargetOffset;
  // Backward PD denominator keeps the spring well conditioned at 120/180 Hz.
  public static Vector3 Force(float mass,Vector3 error,Vector3 relativeVelocity,float dt=1f/120f)
  {
   const float omega=2*Mathf.PI*14;
   dt=Mathf.Clamp(dt,.001f,.033f);
   float denom=1+2*omega*dt+omega*omega*dt*dt;
   return mass*Vector3.ClampMagnitude((omega*omega*error-(2*omega+omega*omega*dt)*relativeVelocity)/denom,100);
  }
  public void Step(Vector3 pinch,float dt)
  {
   if(Body==null||Body.isKinematic||dt<=0)return;
   Vector3 target=Target(pinch);
   var anchor=Body.position+Body.rotation*LocalAnchor;
   var velocity=Vector3.ClampMagnitude((target-PreviousTarget)/dt,2);PreviousTarget=target;
   var error=target-anchor;var relative=Body.GetPointVelocity(anchor)-velocity;
   // Effective mass includes the lever arm: long cloth anchors should rotate
   // the bone without applying the translational mass as excessive torque.
   Vector3 direction=error.sqrMagnitude>1e-10f?error.normalized:Vector3.up;
   var lever=anchor-Body.worldCenterOfMass;
   var principal=Body.rotation*Body.inertiaTensorRotation;
   var torque=Quaternion.Inverse(principal)*Vector3.Cross(lever,direction);
   var inertia=Body.inertiaTensor;
   float inverse=1/Body.mass+torque.x*torque.x/Mathf.Max(inertia.x,1e-8f)+torque.y*torque.y/Mathf.Max(inertia.y,1e-8f)+torque.z*torque.z/Mathf.Max(inertia.z,1e-8f);
   age+=dt;
   var force=Force(1/inverse,error,relative,dt)*Mathf.Clamp01(age/.06f);
   Body.AddForceAtPosition(Vector3.ClampMagnitude(force,2.5f),anchor,ForceMode.Force);
  }
 }
}
