#pragma once

#include "CommandBase.hpp"

// Local experiment only (branch experiment/override-type-probe): reads the override style Archicad
// actually applies to elements and the library part chain behind library part based elements.
class ProbeOverridesCommand : public CommandBase
{
public:
    ProbeOverridesCommand ();
    virtual GS::String GetName () const override;
    virtual GS::ObjectState Execute (const GS::ObjectState& parameters, GS::ProcessControl& processControl) const override;
};
