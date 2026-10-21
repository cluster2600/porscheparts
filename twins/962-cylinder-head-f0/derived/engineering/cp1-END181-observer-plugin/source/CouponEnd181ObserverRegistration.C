// HELD/UNBUILT. Register only the passive observer in the existing Combined host.
#include "ActionFactory.h"
#include "Factory.h"
#include "MooseSyntax.h"
#include "Registry.h"

#include <stdexcept>

registerKnownLabel("CouponEnd181ObserverApp");

// Match MooseApp::loadLibraryAndDependencies REGALL's function-pointer type.
extern "C" void
CouponEnd181ObserverApp__registerAll(Factory * factory,
                                   ActionFactory * action_factory,
                                   Syntax * syntax)
{
  if (!factory || !action_factory || !syntax)
    throw std::invalid_argument("CouponEnd181ObserverApp requires non-null registry arguments.");

  Registry::registerObjectsTo(*factory, {"CouponEnd181ObserverApp"});
}
