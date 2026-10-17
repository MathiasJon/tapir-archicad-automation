#include "ProbeCommands.hpp"
#include "MigrationHelper.hpp"

ProbeOverridesCommand::ProbeOverridesCommand () :
    CommandBase (CommonSchema::NotUsed)
{
}

GS::String ProbeOverridesCommand::GetName () const
{
    return "ProbeOverrides";
}

#ifdef ServerMainVers_2700
static bool GetLibPartByUnID (const char* unID, API_LibPart& libPart)
{
    libPart = {};
    CHTruncate (unID, libPart.ownUnID, sizeof (libPart.ownUnID));
    if (ACAPI_LibraryPart_Search (&libPart, false) != NoError) {
        return false;
    }
    delete libPart.location;
    libPart.location = nullptr;
    return true;
}

static GS::ObjectState LibPartChain (Int32 libInd)
{
    GS::ObjectState os;
    const auto& chain = os.AddList<GS::ObjectState> ("chain");
    API_LibPart libPart = {};
    libPart.index = libInd;
    if (ACAPI_LibraryPart_Get (&libPart) != NoError) {
        return os;
    }
    delete libPart.location;
    libPart.location = nullptr;
    for (int depth = 0; depth < 8; ++depth) {
        chain (GS::ObjectState ("ownUnID", GS::UniString (libPart.ownUnID), "parentUnID", GS::UniString (libPart.parentUnID), "name", GS::UniString (libPart.docu_UName), "typeID", static_cast<Int32> (libPart.typeID)));
        if (libPart.parentUnID[0] == '\0') {
            break;
        }
        API_LibPart parent = {};
        if (!GetLibPartByUnID (libPart.parentUnID, parent)) {
            chain (GS::ObjectState ("missingParent", GS::UniString (libPart.parentUnID)));
            break;
        }
        libPart = parent;
    }
    return os;
}
#endif

GS::ObjectState ProbeOverridesCommand::Execute (const GS::ObjectState& parameters, GS::ProcessControl& /*processControl*/) const
{
    GS::ObjectState response;
#ifdef ServerMainVers_2700
    GS::Array<GS::UniString> elementGuids;
    parameters.Get ("elementGuids", elementGuids);
    const auto& elements = response.AddList<GS::ObjectState> ("elements");
    for (const GS::UniString& guidStr : elementGuids) {
        GS::ObjectState os ("guid", guidStr);
        const API_Guid guid = APIGuidFromString (guidStr.ToCStr ());
        API_OverrideStyle style = {};
        const GSErrCode err = ACAPI_Element_GetActualOverrideStyle (guid, style);
        os.Add ("err", static_cast<Int32> (err));
        if (err == NoError) {
            os.Add ("penOverridden", style.lineMarkerTextPen.hasValue);
            if (style.lineMarkerTextPen.hasValue) {
                os.Add ("pen", static_cast<Int32> (style.lineMarkerTextPen.value));
            }
        }
        API_Element elem = {};
        elem.header.guid = guid;
        if (ACAPI_Element_Get (&elem) == NoError) {
            const API_ElemTypeID typeID = GetElemTypeId (elem.header);
            Int32 libInd = 0;
            if (typeID == API_ZoneID) libInd = elem.zone.libInd;
            else if (typeID == API_ObjectID || typeID == API_LampID) libInd = elem.object.libInd;
            else if (typeID == API_DoorID) libInd = elem.door.openingBase.libInd;
            else if (typeID == API_WindowID) libInd = elem.window.openingBase.libInd;
            else if (typeID == API_LabelID) libInd = elem.label.u.symbol.libInd;
            os.Add ("typeID", static_cast<Int32> (typeID));
            if (libInd > 0) {
                os.Add ("libPart", LibPartChain (libInd));
            }
        }
        elements (os);
    }

    GS::Array<GS::UniString> mainGuids;
    parameters.Get ("mainGuids", mainGuids);
    const auto& parts = response.AddList<GS::ObjectState> ("libraryParts");
    if (!mainGuids.IsEmpty ()) {
        Int32 count = 0;
        ACAPI_LibraryPart_GetNum (&count);
        for (Int32 i = 1; i <= count; ++i) {
            API_LibPart libPart = {};
            libPart.index = i;
            if (ACAPI_LibraryPart_Get (&libPart) != NoError) {
                continue;
            }
            delete libPart.location;
            libPart.location = nullptr;
            GS::UniString own (libPart.ownUnID);
            own.SetToUpperCase ();
            for (const GS::UniString& mainGuid : mainGuids) {
                GS::UniString key = mainGuid;
                key.SetToUpperCase ();
                if (own.Contains (key)) {
                    parts (GS::ObjectState ("mainGuid", mainGuid, "ownUnID", own, "parentUnID", GS::UniString (libPart.parentUnID), "name", GS::UniString (libPart.docu_UName), "index", i));
                }
            }
        }
    }
#else
    UNUSED_PARAMETER (parameters);
#endif
    return response;
}
