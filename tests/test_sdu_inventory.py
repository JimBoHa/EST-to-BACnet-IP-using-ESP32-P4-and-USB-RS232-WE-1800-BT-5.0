import copy
import pytest
from tools.sdu_inventory import FIELDS, build_catalog, registry_preview


def tables():
    t={name:[] for name in FIELDS}
    t['LRM.DB']=[{'Cabinet Number':1,'Slot Position':4,'Function Flag':'L','LRM Address':2,'LRM Type':'3-SDDC1'}]
    obj={'Cabinet Number':1,'Slot Position':4,'Device Address':1,'Function Flag':'L','LRM Address':2,'CCU Index':0,'SDU Index':12,'Label Text':'Sensor α <script>'}
    physical={k:obj[k] for k in ('Cabinet Number','Slot Position','Device Address','Function Flag','CCU Index','SDU Index')}
    physical.update({'Loop Number':1,'Model':'PS','Serial Number':'TEST-1','Short Address':1})
    t['OBJECT.DB']=[obj];t['SENSOR.DB']=[physical]
    return t


def test_real_inventory_keeps_unknown_and_normal_never_observed():
    catalog=build_catalog(tables(),'a'*64,'test-site')
    registry,preview=registry_preview(catalog)
    assert registry['source_mode']=='est3_sdu_v1'
    assert registry['devices'][0]['supported']==0
    assert preview['physical_devices']==1
    assert registry['devices'][0]['address']=='P01 C02 D0001'


def test_rename_and_partial_export_preserve_identity_and_no_retirement():
    t=tables();old=build_catalog(t,'a'*64,'site');registry,_=registry_preview(old)
    t['OBJECT.DB'][0]['Label Text']='new name'
    new=build_catalog(t,'b'*64,'site')
    renamed,preview=registry_preview(new,registry,prior_catalog=old)
    assert renamed['devices'][0]['instances']==registry['devices'][0]['instances']
    assert renamed['devices'][0]['binding_epoch']==1
    assert preview['counts']=={'rename':1}
    partial=copy.deepcopy(new);partial['devices']=[]
    retained,preview=registry_preview(partial,renamed,prior_catalog=new)
    assert len(retained['devices'])==1 and not retained['devices'][0]['retired']
    assert preview['counts']=={'missing_from_backup_retained_for_review':1}


def test_replacement_or_unknown_prior_quarantined():
    t=tables();old=build_catalog(t,'a'*64,'site');registry,_=registry_preview(old)
    with pytest.raises(ValueError,match='previous source'):registry_preview(old,registry)
    t['SENSOR.DB'][0]['Serial Number']='OTHER'
    new=build_catalog(t,'b'*64,'site')
    with pytest.raises(ValueError,match='identity change'):registry_preview(new,registry,prior_catalog=old)


@pytest.mark.parametrize('fault',['duplicate','missing','lrm','type','nul'])
def test_invalid_joins_rejected(fault):
    t=tables()
    if fault=='duplicate':t['OBJECT.DB']*=2
    if fault=='missing':t['OBJECT.DB']=[]
    if fault=='lrm':t['OBJECT.DB'][0]['LRM Address']=8
    if fault=='type':t['SENSOR.DB'][0]['CCU Index']=4
    if fault=='nul':t['OBJECT.DB'][0]['Label Text']='bad\0text'
    with pytest.raises(ValueError):build_catalog(t,'a'*64,'site')
