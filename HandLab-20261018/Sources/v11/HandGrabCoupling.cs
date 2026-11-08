using UnityEngine;

namespace MGFR.BareHands
{
 public sealed class HandGrabCoupling:MonoBehaviour
 {
  public Rigidbody Body;
  public Vector3 LocalAnchor,PreviousTarget;
  public Collider Surface;
  public static Vector3 Force(float mass,Vector3 error,Vector3 relativeVelocity)
  {
   const float omega=2*Mathf.PI*6;
   return mass*Vector3.ClampMagnitude(omega*omega*error-2*omega*relativeVelocity,18);
  }
  public void Step(Vector3 target,float dt)
  {
   var anchor=Body.position+Body.rotation*LocalAnchor;
   var velocity=(target-PreviousTarget)/dt;PreviousTarget=target;
   Body.AddForceAtPosition(Force(Body.mass,target-anchor,Body.GetPointVelocity(anchor)-velocity),anchor,ForceMode.Force);
  }
 }
}
