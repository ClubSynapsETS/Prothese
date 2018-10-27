


/* Service: Myo Mouvement
 *      Service UUID : 69a0977f-8fd5-434f-b506-0000658c1749
 *      Primary: is_primary
 *
 *   
 *   Characteristics //charact 128 bit uuid = Service_uuid | (CHRC_UUID << 32)
 *   {
 *      Mouvement
 *          UUID: 0x0001 
 *          flags: Notify
 *          Description: Server will output upon processing raw Myo data the desired mouvememnt
 *                       for the prosthesis. It will notify the client that a new mouvement is
 *                       required.
 *
 *      Mode
 *          UUID: 0x0002
 *          flags: Read
 *
 *          Description: It Will contain the desired mode for the prosthesis. Currently three 
 *          modes are defined: Myo_dirconnect, a direct connection to the myo.
 *                             Demo_mode, Alternate between pre-programe mouvements.
 *                             Human_crtl_mode, subscribe to MouvementChrc.
 *
 *      Logs
 *          UUID: 0x0003
 *          flags: Write
 *
 *          Description: Send information important to the main application, such as current 
 *                       battery level or how errors were handled.
 *   }
 */

#define MYO_MOUVEMENT_SERVICE_UUID { \
    0x49, 0x17, 0x8c, 0x65,          \
    0x00, 0x00, 0x06, 0xb5,          \
    0x4f, 0x43, 0xd5, 0x8f,          \
    0x7f, 0x97, 0xa0, 0x69,          \
}

typedef enum 
{
    MouvementChrc       = 0x0001,
    ModeChrc            = 0x0002,
    LogsChrc            = 0x0003,
} myomv_chrc;

// Defined prosthesis mouvements.
enum prot_mv 
{
    MV_WRIST_FLEXION,
    MV_WRIST_EXTENSION,
    MV_TRIPODAL_GRASPING,
    MV_SPHERICAL_GRASPING,
    MV_CYLINDRICAL_GRAPSING,
    MV_KEY_GRASPING,
    MV_HAND_OPEN,
    MV_HAND_CLOSE,
    MV_RESTING
};




