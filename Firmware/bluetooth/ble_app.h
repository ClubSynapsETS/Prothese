#include "esp_bt.h"
#include "esp_bt_device.h"
#include "esp_gattc_api.h"

// application profile definition
struct gattc_profile_inst {
    esp_gattc_cb_t gattc_cb;
    uint16_t gattc_if;
    uint16_t app_id;
    uint16_t conn_id;
    uint16_t service_start_handle;
    uint16_t service_end_handle;
    uint16_t char_handle;
    esp_bd_addr_t remote_bda;
};

/* declare public functions */
void bt_app_launch(void);
