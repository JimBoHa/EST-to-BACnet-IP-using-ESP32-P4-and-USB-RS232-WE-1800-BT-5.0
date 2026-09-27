#include "bacnet_gateway.h"
#include "bacnet/basic/services.h"
#include "bacnet/basic/object/device.h"
#include "bacnet/basic/object/bi.h"
#include "bacnet/datalink/bip.h"
#include "bacnet/basic/tsm/tsm.h"
#include <string.h>
#include <stdio.h>

static gw_registry *active_registry;
static uint8_t pdu[MAX_PDU];
static bool readonly_write(BACNET_WRITE_PROPERTY_DATA *r) {r->error_class=ERROR_CLASS_PROPERTY;r->error_code=ERROR_CODE_WRITE_ACCESS_DENIED;return false;}
static object_functions_t objects[]={
    {.Object_Type=OBJECT_DEVICE,.Object_Count=Device_Count,.Object_Index_To_Instance=Device_Index_To_Instance,.Object_Valid_Instance=Device_Valid_Object_Instance_Number,.Object_Name=Device_Object_Name,.Object_Read_Property=Device_Read_Property_Local,.Object_Write_Property=readonly_write,.Object_RPM_List=Device_Property_Lists},
    {.Object_Type=OBJECT_BINARY_INPUT,.Object_Init=Binary_Input_Init,.Object_Count=Binary_Input_Count,.Object_Index_To_Instance=Binary_Input_Index_To_Instance,.Object_Valid_Instance=Binary_Input_Valid_Instance,.Object_Name=Binary_Input_Object_Name,.Object_Read_Property=Binary_Input_Read_Property,.Object_Write_Property=readonly_write,.Object_RPM_List=Binary_Input_Property_Lists},
    {.Object_Type=MAX_BACNET_OBJECT_TYPE}
};
static void update_values(bool usb_connected) {
    uint64_t now=bg_now();
    Binary_Input_Present_Value_Set(1,BINARY_INACTIVE);
    Binary_Input_Present_Value_Set(2,usb_connected?BINARY_ACTIVE:BINARY_INACTIVE);
    Binary_Input_Present_Value_Set(3,active_registry&&active_registry->count?BINARY_ACTIVE:BINARY_INACTIVE);
    bool valid=active_registry&&active_registry->count;
    if(active_registry) for(size_t i=0;i<active_registry->count;i++) {
        gw_device *d=&active_registry->devices[i];
        bool dv=gw_data_valid(d,now);if(!d->retired&&!dv)valid=false;
        for(unsigned k=0;k<5;k++) {
            bool v=k==4?dv:d->conditions[k].value;
            bool good=k==4?!d->retired:gw_condition_valid(d,k,now);
            Binary_Input_Present_Value_Set(d->instances[k],v?BINARY_ACTIVE:BINARY_INACTIVE);
            Binary_Input_Reliability_Set(d->instances[k],good?RELIABILITY_NO_FAULT_DETECTED:RELIABILITY_COMMUNICATION_FAILURE);
        }
    }
    Binary_Input_Present_Value_Set(4,valid?BINARY_ACTIVE:BINARY_INACTIVE);
}
bool bg_registry(gw_registry *registry) {
    for(size_t i=0;i<registry->count;i++) for(unsigned k=0;k<5;k++) {
        uint32_t id=registry->devices[i].instances[k];
        if(Binary_Input_Create(id)!=id)return false;
        Binary_Input_Write_Disable(id);
        Binary_Input_Description_Set(id,registry->devices[i].label);
    }
    active_registry=registry;Device_Inc_Database_Revision();return true;
}
bool bg_start(uint32_t instance,const char *bind_ip,uint16_t port,const char *broadcast) {
    address_init();Device_Init(objects);Device_Set_Object_Instance_Number(instance);
    const char *name=instance==3899001?"SIMULATION_ONLY EST3 lab":"EST3 RX-only bench gateway";
    BACNET_CHARACTER_STRING object_name;characterstring_init_ansi(&object_name,name);Device_Set_Object_Name(&object_name);
    Device_Set_Model_Name("EST3 P4 draft",strlen("EST3 P4 draft"));
    Device_Set_Vendor_Identifier(65535);
    Device_Set_Vendor_Name("UNASSIGNED LAB ONLY",strlen("UNASSIGNED LAB ONLY"));
    for(unsigned k=1;k<=4;k++) {if(Binary_Input_Create(k)!=k)return false;Binary_Input_Write_Disable(k);}
    Binary_Input_Description_Set(1,"Real ECP enabled (always false in this release)");
    Binary_Input_Description_Set(2,"USB FTDI connected; does not establish panel communication");
    Binary_Input_Description_Set(3,"Durable device registry present");
    Binary_Input_Description_Set(4,"All active required conditions fresh and synchronized");
    apdu_set_unconfirmed_handler(SERVICE_UNCONFIRMED_WHO_IS,handler_who_is_unicast);
    apdu_set_confirmed_handler(SERVICE_CONFIRMED_READ_PROPERTY,handler_read_property);
    apdu_set_confirmed_handler(SERVICE_CONFIRMED_READ_PROP_MULTIPLE,handler_read_property_multiple);
    apdu_set_unrecognized_service_handler_handler(handler_unrecognized_service);
    bip_set_port(port);bg_configure_address(bind_ip,broadcast);
    return bip_init((char*)bind_ip);
}
void bg_poll(unsigned timeout,bool usb_connected) {
    static uint64_t last_refresh;
    BACNET_ADDRESS source;uint16_t n=bip_receive(&source,pdu,sizeof(pdu),timeout);
    if(n || bg_now()-last_refresh>=250) {update_values(usb_connected);last_refresh=bg_now();}
    if(n)npdu_handler(&source,pdu,n);
}
